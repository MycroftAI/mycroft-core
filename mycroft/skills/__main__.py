# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Daemon launched at startup to handle skill activities.

In this repo, you will not find an entry called mycroft-skills in the bin
directory.  The executable gets added to the bin directory when installed
(see setup.py)
"""
import time
from threading import Event

import mycroft.lock
from msm.exceptions import MsmException

from mycroft import dialog
from mycroft.api import is_paired, BackendDown, DeviceApi
from mycroft.audio import wait_while_speaking
from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.messagebus.client import MessageBusClient
from mycroft.messagebus.message import Message
from mycroft.util import (
    connected,
    create_echo_function,
    create_daemon,
    reset_sigint_handler,
    wait_for_exit_signal
)
from mycroft.util.lang import set_active_lang
from mycroft.util.log import LOG
from .core import FallbackSkill
from .event_scheduler import EventScheduler
from .intent_service import IntentService
from .padatious_service import PadatiousService
from .skill_manager import SkillManager

RASPBERRY_PI_PLATFORMS = ('mycroft_mark_1', 'picroft', 'mycroft_mark_2pi')


class DevicePrimer(object):
    """Container handling the device preparation.

    Arguments:
        message_bus_client: Bus client used to interact with the system
        config (dict): Mycroft configuration
    """
    def __init__(self, message_bus_client, config):
        self.bus = message_bus_client
        self.platform = config['enclosure'].get("platform", "unknown")
        self.enclosure = EnclosureAPI(self.bus)
        self.is_paired = False
        self.backend_down = False
        # Remember "now" at startup.  Used to detect clock changes.

    def prepare_device(self):
        """Internet dependent updates of various aspects of the device."""
        self._get_pairing_status()
        self._update_system_clock()
        self._update_system()
        # Above will block during update process and kill this instance if
        # new software is installed

        if self.backend_down:
            self._notify_backend_down()
        else:
            self._display_skill_loading_notification()
            self.bus.emit(Message('mycroft.internet.connected'))
            self._ensure_device_is_paired()
            self._update_device_attributes_on_backend()

    def _get_pairing_status(self):
        """Set an instance attribute indicating the device's pairing status"""
        try:
            self.is_paired = is_paired(ignore_errors=False)
        except BackendDown:
            LOG.error('Cannot complete device updates due to backend issues.')
            self.backend_down = True

        if self.is_paired:
            LOG.info('Device is paired')

    def _update_system_clock(self):
        """Force a sync of the local clock with the Network Time Protocol.

        The NTP sync is only forced on Raspberry Pi based devices.  The
        assumption being that these devices are only running Mycroft services.
        We don't want to sync the time on a Linux desktop device, for example,
        because it could have a negative impact on other software running on
        that device.
        """
        if self.platform in RASPBERRY_PI_PLATFORMS:
            LOG.info('Updating the system clock via NTP...')
            if self.is_paired:
                # Only display time sync message when paired because the prompt
                # to go to home.mycroft.ai will be displayed by the pairing
                # skill when pairing
                self.enclosure.mouth_text(dialog.get("message_synching.clock"))
            self.bus.wait_for_response(
                Message('system.ntp.sync'),
                'system.ntp.sync.complete',
                15
            )

    def _notify_backend_down(self):
        """Notify user of inability to communicate with the backend."""
        self._speak_dialog(dialog_id="backend.down")
        self.bus.emit(Message("backend.down"))

    def _display_skill_loading_notification(self):
        """Indicate to the user that skills are being loaded."""
        self.enclosure.eyes_color(189, 183, 107)  # dark khaki
        self.enclosure.mouth_text(dialog.get("message_loading.skills"))

    def _ensure_device_is_paired(self):
        """Determine if device is paired, if not automatically start pairing.

        Pairing cannot be performed if there is no connection to the back end.
        So skip pairing if the backend is down.
        """
        if not self.is_paired and not self.backend_down:
            LOG.info('Device not paired, invoking the pairing skill')
            payload = dict(utterances=["pair my device"], lang="en-us")
            self.bus.emit(Message("recognizer_loop:utterance", payload))

    def _update_device_attributes_on_backend(self):
        """Communicate version information to the backend.

        The backend tracks core version, enclosure version, platform build
        and platform name for each device, if it is known.
        """
        if self.is_paired:
            LOG.info('Sending updated device attributes to the backend...')
            try:
                api = DeviceApi()
                api.update_version()
            except Exception:
                self._notify_backend_down()

    def _update_system(self):
        """Emit an update event that will be handled by the admin service."""
        if not self.is_paired:
            LOG.info('Attempting system update...')
            self.bus.emit(Message('system.update'))
            msg = Message(
                'system.update',
                dict(paired=self.is_paired, platform=self.platform)
            )
            resp = self.bus.wait_for_response(msg, 'system.update.processing')

            if resp and (resp.data or {}).get('processing', True):
                self.bus.wait_for_response(
                    Message('system.update.waiting'),
                    'system.update.complete',
                    1000
                )

    def _speak_dialog(self, dialog_id, wait=False):
        data = {'utterance': dialog.get(dialog_id)}
        self.bus.emit(Message("speak", data))
        if wait:
            wait_while_speaking()


def main():
    reset_sigint_handler()
    # Create PID file, prevent multiple instances of this service
    mycroft.lock.Lock('skills')
    config = Configuration.get()
    # Set the active lang to match the configured one
    set_active_lang(config.get('lang', 'en-us'))

    # Connect this process to the Mycroft message bus
    bus = _start_message_bus_client()
    _register_intent_services(bus)
    event_scheduler = EventScheduler(bus)
    skill_manager = _initialize_skill_manager(bus)

    _wait_for_internet_connection()

    if skill_manager is None:
        skill_manager = _initialize_skill_manager(bus)

    device_primer = DevicePrimer(bus, config)
    device_primer.prepare_device()
    skill_manager.start()

    wait_for_exit_signal()
    shutdown(skill_manager, event_scheduler)


def _start_message_bus_client():
    """Start the bus client daemon and wait for connection."""
    bus = MessageBusClient()
    Configuration.set_config_update_handlers(bus)
    bus_connected = Event()
    bus.on('message', create_echo_function('SKILLS'))
    # Set the bus connected event when connection is established
    bus.once('open', bus_connected.set)
    create_daemon(bus.run_forever)

    # Wait for connection
    bus_connected.wait()
    LOG.info('Connected to messagebus')

    return bus


def _register_intent_services(bus):
    """Start up the all intent services and connect them as needed.

    Arguments:
        bus: messagebus client to register the services on
    """
    service = IntentService(bus)
    try:
        PadatiousService(bus, service)
    except Exception as e:
        LOG.exception('Failed to create padatious handlers '
                      '({})'.format(repr(e)))

    # Register handler to trigger fallback system
    bus.on('intent_failure', FallbackSkill.make_intent_failure_handler(bus))


def _initialize_skill_manager(bus):
    """Create a thread that monitors the loaded skills, looking for updates

    Returns:
        SkillManager instance or None if it couldn't be initialized
    """
    try:
        skill_manager = SkillManager(bus)
        skill_manager.load_priority()
    except MsmException:
        # skill manager couldn't be created, wait for network connection and
        # retry
        skill_manager = None
        LOG.info(
            'MSM is uninitialized and requires network connection to fetch '
            'skill information\nWill retry after internet connection is '
            'established.'
        )

    return skill_manager


def _wait_for_internet_connection():
    while not connected():
        time.sleep(1)


def shutdown(skill_manager, event_scheduler):
    LOG.info('Shutting down skill service')
    if event_scheduler is not None:
        event_scheduler.shutdown()
    # Terminate all running threads that update skills
    if skill_manager is not None:
        skill_manager.stop()
        skill_manager.join()
    LOG.info('Skill service shutdown complete!')


if __name__ == "__main__":
    main()
