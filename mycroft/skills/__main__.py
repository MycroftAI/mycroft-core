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
from threading import Timer

from msm.exceptions import MsmException

from mycroft import dialog
from mycroft.api import is_paired, BackendDown, DeviceApi
from mycroft.audio import wait_while_speaking
from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.lock import Lock
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
ONE_HOUR = 3600

bus = None  # Mycroft message bus reference, see "mycroft.messagebus"
skill_service = None

# Remember "now" at startup.  Used to detect clock changes.
start_ticks = time.monotonic()
start_clock = time.time()


class SkillService(object):
    def __init__(self, message_bus_client, config):
        self.bus = message_bus_client
        self.config = config
        self._define_message_bus_handlers()
        self.event_scheduler = None
        self.skill_manager = None

    def _define_message_bus_handlers(self):
        self.bus.on('message', create_echo_function('SKILLS'))
        self.bus.on(
            'intent_failure',
            FallbackSkill.make_intent_failure_handler(self.bus)
        )

    def start(self):
        self._start_intent_services()
        self.event_scheduler = EventScheduler(self.bus)
        self._start_skill_manager()

    def _start_intent_services(self):
        """Instantiate the Adapt and Padatious intent managers.

        The intent managers convert utterances to intents, which used to invoke
        the skill system.  Skill handlers define intents that, when matched,
        will execute the code within the skill handler.

        When no match is found for the intent, an intent_failu re message is
        emitted, which invokes the fallback mechanism.
        """
        LOG.info('Starting Adapt and Padatious intent services...')
        service = IntentService(self.bus)  # Adapt
        try:
            PadatiousService(self.bus, service)
        except Exception as e:
            LOG.error('Failed to create Padatious intent handlers')
            LOG.exception(e)

    def _start_skill_manager(self):
        """Create a thread that monitors loaded skills looking for updates."""
        LOG.info('Starting the skill manager...')
        # TODO: if this needs an internet connection, don't start it so soon
        try:
            self.skill_manager = SkillManager(self.bus)
        except MsmException:
            # skill manager couldn't be created, wait for network connection
            # and retry
            LOG.error(
                'Msm is uninitialized and requires network connection to fetch'
                'skill information\n Waiting for network connection...'
            )
            while not connected():
                time.sleep(30)
            self.skill_manager = SkillManager(self.bus)

        self.skill_manager.daemon = True

        # Wait until priority skills have been loaded before checking
        # network connection
        self.skill_manager.load_priority()
        self.skill_manager.start()


class DevicePrimer(object):
    def __init__(self, message_bus_client, config):
        self.bus = message_bus_client
        self.platform = config['enclosure'].get("platform", "unknown")
        self.enclosure = None
        self.is_paired = False
        self.backend_down = False

    def prepare_device(self):
        """Internet dependent updates of various aspects of the device."""
        self.enclosure = EnclosureAPI(self.bus)
        self._get_pairing_status()
        self._update_system_clock()
        self._attempt_system_update()
        reboot = self._check_time_skew()
        if not reboot:
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

    def _update_system_clock(self):
        """Force a sync of the local clock with the Network Time Protocol.

        The NTP sync is only forced on Raspberry Pi based devices.  The
        assumption being that these devices are only running Mycroft services.
        We don't want to sync the time on a Linux desktop device, for example,
        because it could have a negative impact on other software running on
        that device.
        """
        LOG.info('Updating the system clock via NTP...')
        if self.platform in RASPBERRY_PI_PLATFORMS:
            if self.is_paired:
                # Only display time sync message when paired because the prompt
                # to go to home.mycroft.ai will be displayed by the pairing
                # skill when pairing
                self.enclosure.mouth_text(dialog.get("message_synching.clock"))
            bus.wait_for_response(
                Message('system.ntp.sync'),
                'system.ntp.sync.complete',
                15
            )

    def _check_time_skew(self):
        """If the NTP sync skewed system time significantly, reboot.

        If system time moved by over an hour in the NTP sync, force a reboot to
        prevent weird things from occurring due to the 'time warp'.
        """
        reboot = False
        skew = abs((time.monotonic() - start_ticks) -
                   (time.time() - start_clock))
        if skew > ONE_HOUR:
            LOG.warning(
                'Clock sync altered system time by more than one hour,'
                ' rebooting...'
            )
            data = {'utterance': dialog.get("time.changed.reboot")}
            bus.emit(Message("speak", data))
            wait_while_speaking()
            # provide visual indicators of the reboot
            self.enclosure.mouth_text(dialog.get("message_rebooting"))
            self.enclosure.eyes_color(70, 65, 69)  # soft gray
            self.enclosure.eyes_spin()
            # give the system time to finish processing enclosure messages
            time.sleep(1.0)
            # reboot
            bus.emit(Message("system.reboot"))
            reboot = True
        else:
            bus.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)

        return reboot

    def _notify_backend_down(self):
        """Notify user of inability to communicate with the backend."""
        data = {'utterance': dialog.get("backend.down")}
        self.bus.emit(Message("speak", data))
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
            except BackendDown:
                data = {'utterance': dialog.get("backend.down")}
                bus.emit(Message("speak", data))
                bus.emit(Message("backend.down"))

    def _attempt_system_update(self):
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


def main():
    global bus
    reset_sigint_handler()
    # Create PID file, prevent multiple instances of this service
    Lock('skills')
    # Connect this Skill management process to the Mycroft message bus
    bus = MessageBusClient()
    bus.once('open', startup)
    create_daemon(bus.run_forever)
    wait_for_exit_signal()
    shutdown()


def startup():
    global bus, skill_service
    config_manager = Configuration()
    config_manager.set_config_update_handlers(bus)
    config = config_manager.get()
    set_active_lang(config.get('lang', 'en-us'))
    skill_service = SkillService(bus, config)
    skill_service.start()
    _prepare_device(config)
    LOG.info('Completed skill service startup!')


def _prepare_device(config):
    global bus
    if connected():
        device_primer = DevicePrimer(bus, config)
        device_primer.prepare_device()
    else:
        thread = Timer(1, _prepare_device)
        thread.daemon = True
        thread.start()


def shutdown():
    LOG.info('Shutting down skill service')
    global skill_service
    if skill_service.event_scheduler is not None:
        skill_service.event_scheduler.shutdown()
    # Terminate all running threads that update skills
    if skill_service.skill_manager is not None:
        skill_service.skill_manager.stop()
        skill_service.skill_manager.join()
    LOG.info('Completed skill service shutdown!')


if __name__ == "__main__":
    main()
