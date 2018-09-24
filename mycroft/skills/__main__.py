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
import time
from threading import Timer
import mycroft.lock
from mycroft import dialog
from mycroft.api import is_paired, BackendDown
from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import (
    connected, wait_while_speaking, reset_sigint_handler,
    create_echo_function, create_daemon, wait_for_exit_signal
)

from .skill_manager import SkillManager
from .core import FallbackSkill
from .event_scheduler import EventScheduler
from .intent_service import IntentService
from .padatious_service import PadatiousService

bus = None  # Mycroft messagebus reference, see "mycroft.messagebus"
event_scheduler = None
skill_manager = None

# Remember "now" at startup.  Used to detect clock changes.
start_ticks = time.monotonic()
start_clock = time.time()


def connect():
    global bus
    bus.run_forever()


def _starting_up():
    """
        Start loading skills.

        Starts
        - SkillManager to load/reloading of skills when needed
        - a timer to check for internet connection
        - adapt intent service
        - padatious intent service
    """
    global bus, skill_manager, event_scheduler

    bus.on('intent_failure', FallbackSkill.make_intent_failure_handler(bus))

    # Create the Intent manager, which converts utterances to intents
    # This is the heart of the voice invoked skill system

    service = IntentService(bus)
    PadatiousService(bus, service)
    event_scheduler = EventScheduler(bus)

    # Create a thread that monitors the loaded skills, looking for updates
    skill_manager = SkillManager(bus)
    skill_manager.daemon = True
    # Wait until skills have been loaded once before starting to check
    # network connection
    skill_manager.load_priority()
    skill_manager.start()
    check_connection()


def check_connection():
    """
        Check for network connection. If not paired trigger pairing.
        Runs as a Timer every second until connection is detected.
    """
    if connected():
        enclosure = EnclosureAPI(bus)

        if is_paired():
            # Skip the sync message when unpaired because the prompt to go to
            # home.mycrof.ai will be displayed by the pairing skill
            enclosure.mouth_text(dialog.get("message_synching.clock"))

        # Force a sync of the local clock with the internet
        config = Configuration.get()
        platform = config['enclosure'].get("platform", "unknown")
        if platform in ['mycroft_mark_1', 'picroft']:
            bus.emit(Message("system.ntp.sync"))
            time.sleep(15)  # TODO: Generate/listen for a message response...

        # Check if the time skewed significantly.  If so, reboot
        skew = abs((time.monotonic() - start_ticks) -
                   (time.time() - start_clock))
        if skew > 60 * 60:
            # Time moved by over an hour in the NTP sync. Force a reboot to
            # prevent weird things from occcurring due to the 'time warp'.
            #
            data = {'utterance': dialog.get("time.changed.reboot")}
            bus.emit(Message("speak", data))
            wait_while_speaking()

            # provide visual indicators of the reboot
            enclosure.mouth_text(dialog.get("message_rebooting"))
            enclosure.eyes_color(70, 65, 69)  # soft gray
            enclosure.eyes_spin()

            # give the system time to finish processing enclosure messages
            time.sleep(1.0)

            # reboot
            bus.emit(Message("system.reboot"))
            return
        else:
            bus.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)

        bus.emit(Message('mycroft.internet.connected'))
        # check for pairing, if not automatically start pairing
        try:
            if not is_paired(ignore_errors=False):
                payload = {
                    'utterances': ["pair my device"],
                    'lang': "en-us"
                }
                bus.emit(Message("recognizer_loop:utterance", payload))
            else:
                from mycroft.api import DeviceApi
                api = DeviceApi()
                api.update_version()
        except BackendDown:
            data = {'utterance': dialog.get("backend.down")}
            bus.emit(Message("speak", data))
            bus.emit(Message("backend.down"))

    else:
        thread = Timer(1, check_connection)
        thread.daemon = True
        thread.start()


def main():
    global bus
    reset_sigint_handler()
    # Create PID file, prevent multiple instancesof this service
    mycroft.lock.Lock('skills')
    # Connect this Skill management process to the Mycroft Messagebus
    bus = WebsocketClient()
    Configuration.init(bus)

    bus.on('message', create_echo_function('SKILLS'))
    # Startup will be called after the connection with the Messagebus is done
    bus.once('open', _starting_up)

    create_daemon(bus.run_forever)
    wait_for_exit_signal()
    shutdown()


def shutdown():
    if event_scheduler:
        event_scheduler.shutdown()

    # Terminate all running threads that update skills
    if skill_manager:
        skill_manager.stop()
        skill_manager.join()


if __name__ == "__main__":
    main()
