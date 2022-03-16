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

import mycroft.lock
from mycroft.api import is_paired
from mycroft.configuration import setup_locale
from mycroft.enclosure.api import EnclosureAPI
from mycroft.skills.api import SkillApi
from mycroft.skills.core import FallbackSkill
from mycroft.skills.event_scheduler import EventScheduler
from mycroft.skills.intent_service import IntentService
from mycroft.skills.skill_manager import SkillManager, on_error, on_stopping, on_ready, on_alive, on_started
from mycroft.util import (
    reset_sigint_handler,
    start_message_bus_client,
    wait_for_exit_signal
)
from mycroft.util.log import LOG

RASPBERRY_PI_PLATFORMS = ('mycroft_mark_1', 'picroft', 'mycroft_mark_2pi')


class DevicePrimer:
    """DEPRECATED: this class has been fully deprecated, stop using it!
    Only here to provide public api compatibility but it does absolutely nothing!
    """

    def __init__(self, message_bus_client, config=None):
        self.bus = message_bus_client
        self.platform = "unknown"
        self.enclosure = EnclosureAPI(self.bus)
        self.backend_down = False

    @property
    def is_paired(self):
        return is_paired()

    def prepare_device(self):
        """Internet dependent updates of various aspects of the device."""
        LOG.warning("DevicePrimer has been deprecated!")


def main(alive_hook=on_alive, started_hook=on_started, ready_hook=on_ready,
         error_hook=on_error, stopping_hook=on_stopping, watchdog=None):
    """Create a thread that monitors the loaded skills, looking for updates

    Returns:
        SkillManager instance or None if it couldn't be initialized
    """
    reset_sigint_handler()
    # Create PID file, prevent multiple instances of this service
    mycroft.lock.Lock('skills')

    setup_locale()

    # Connect this process to the Mycroft message bus
    bus = start_message_bus_client("SKILLS")
    _register_intent_services(bus)
    event_scheduler = EventScheduler(bus, autostart=False)
    event_scheduler.setDaemon(True)
    event_scheduler.start()
    SkillApi.connect_bus(bus)
    skill_manager = SkillManager(bus, watchdog,
                                 alive_hook=alive_hook,
                                 started_hook=started_hook,
                                 stopping_hook=stopping_hook,
                                 ready_hook=ready_hook,
                                 error_hook=error_hook)

    skill_manager.start()

    wait_for_exit_signal()

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
