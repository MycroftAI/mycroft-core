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

import mycroft.lock
from mycroft import dialog
from mycroft.api import is_paired, BackendDown, DeviceApi
from mycroft.audio import wait_while_speaking
from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration, setup_locale
from mycroft.messagebus.message import Message
from mycroft.util import (
    connected,
    reset_sigint_handler,
    start_message_bus_client,
    wait_for_exit_signal
)
from mycroft.util.log import LOG
from mycroft.util.process_utils import ProcessStatus, StatusCallbackMap

from mycroft.skills.api import SkillApi
from mycroft.skills.core import FallbackSkill
from mycroft.skills.event_scheduler import EventScheduler
from mycroft.skills.intent_service import IntentService
from mycroft.skills.skill_manager import SkillManager
from mycroft.skills.msm_wrapper import MsmException

RASPBERRY_PI_PLATFORMS = ('mycroft_mark_1', 'picroft', 'mycroft_mark_2pi')


class DevicePrimer:
    """Container handling the device preparation.

    Args:
        message_bus_client: Bus client used to interact with the system
        config (dict): Mycroft configuration
    """
    def __init__(self, message_bus_client, config):
        self.bus = message_bus_client
        self.platform = config['enclosure'].get("platform", "unknown")

        # force flag is for backwards compat with regular mycroft-core
        # assumptions
        force = config['enclosure'].get("force_mycroft_ntp") and \
                self.platform in RASPBERRY_PI_PLATFORMS

        self.do_ntp_sync = config['enclosure'].get("ntp_sync_on_boot") or force

        self.enclosure = EnclosureAPI(self.bus)
        self.is_paired = False
        self.backend_down = False
        # Remember "now" at startup.  Used to detect clock changes.

    def prepare_device(self):
        """Internet dependent updates of various aspects of the device."""
        if connected():
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
        else:
            LOG.warning('Cannot prime device because there is no '
                        'internet connection, this is OK 99% of the time, '
                        'but it might affect integration with mycroft '
                        'backend')

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
        if self.do_ntp_sync:
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
            self.bus.emit(Message("mycroft.not.paired"))

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


def on_started():
    LOG.info('Skills service is starting up.')


def on_alive():
    LOG.info('Skills service is alive.')


def on_ready():
    LOG.info('Skills service is ready.')


def on_error(e='Unknown'):
    LOG.info('Skills service failed to launch ({})'.format(repr(e)))


def on_stopping():
    LOG.info('Skills service is shutting down...')


def main(alive_hook=on_alive, started_hook=on_started, ready_hook=on_ready,
         error_hook=on_error, stopping_hook=on_stopping, watchdog=None):
    reset_sigint_handler()
    # Create PID file, prevent multiple instances of this service
    mycroft.lock.Lock('skills')

    callbacks = StatusCallbackMap(on_started=started_hook,
                                  on_alive=alive_hook,
                                  on_ready=ready_hook,
                                  on_error=error_hook,
                                  on_stopping=stopping_hook)
    status = ProcessStatus('skills', callback_map=callbacks)
    status.set_started()

    config = Configuration.get()
    setup_locale()

    # Connect this process to the Mycroft message bus
    bus = start_message_bus_client("SKILLS")
    _register_intent_services(bus)
    event_scheduler = EventScheduler(bus, autostart=False)
    event_scheduler.setDaemon(True)
    event_scheduler.start()
    SkillApi.connect_bus(bus)
    skill_manager = _initialize_skill_manager(bus, watchdog)

    status.bind(bus)
    status.set_alive()

    if config["skills"].get("wait_for_internet", True):
        _wait_for_internet_connection()

    if skill_manager is None:
        skill_manager = _initialize_skill_manager(bus, watchdog)

    device_primer = DevicePrimer(bus, config)
    device_primer.prepare_device()
    skill_manager.start()
    while not skill_manager.is_alive():
        time.sleep(0.1)

    while not skill_manager.is_all_loaded():
        time.sleep(0.1)
    status.set_ready()

    wait_for_exit_signal()
    status.set_stopping()
    shutdown(skill_manager, event_scheduler)


def _register_intent_services(bus):
    """Start up the all intent services and connect them as needed.

    Args:
        bus: messagebus client to register the services on
    """
    service = IntentService(bus)
    # Register handler to trigger fallback system
    bus.on(
        'mycroft.skills.fallback',
        FallbackSkill.make_intent_failure_handler(bus)
    )
    return service


def _initialize_skill_manager(bus, watchdog):
    """Create a thread that monitors the loaded skills, looking for updates

    Returns:
        SkillManager instance or None if it couldn't be initialized
    """
    try:
        skill_manager = SkillManager(bus, watchdog)
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
    LOG.info('Shutting down Skills service')
    if event_scheduler is not None:
        event_scheduler.shutdown()
    # Terminate all running threads that update skills
    if skill_manager is not None:
        skill_manager.stop()
        skill_manager.join()
    LOG.info('Skills service shutdown complete!')


if __name__ == "__main__":
    main()
