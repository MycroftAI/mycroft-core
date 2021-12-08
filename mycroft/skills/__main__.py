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

from lingua_franca import load_languages

import mycroft.lock
from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util import (
    connected,
    reset_sigint_handler,
    start_message_bus_client,
    wait_for_exit_signal
)
from mycroft.util.log import LOG
from mycroft.util.process_utils import ProcessStatus, StatusCallbackMap
from .api import SkillApi
from .core import FallbackSkill
from .event_scheduler import EventScheduler
from .intent_service import IntentService
from .skill_manager import SkillManager


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
    bus = start_message_bus_client("SKILLS")
    callbacks = StatusCallbackMap(on_started=started_hook,
                                  on_alive=alive_hook,
                                  on_ready=ready_hook,
                                  on_error=error_hook,
                                  on_stopping=stopping_hook)
    status = ProcessStatus('skills', bus, callbacks)
    _set_initialize_started_status(bus, status)
    _load_language()
    _register_intent_services(bus)
    event_scheduler = EventScheduler(bus)
    SkillApi.connect_bus(bus)

    # _wait_for_internet_connection()
    skill_manager = SkillManager(bus, watchdog)
    skill_manager.load_on_startup()

    while not skill_manager.is_all_loaded():
        time.sleep(0.1)
    _set_initialize_ended_status(bus, status)
    skill_manager.start()

    wait_for_exit_signal()
    shutdown(skill_manager, event_scheduler, status)


def _set_initialize_started_status(bus, status):
    bus.emit(Message("skills.initialize.started"))
    status.set_started()


def _load_language():
    config = Configuration.get()
    lang_code = config.get("lang", "en-us")
    load_languages([lang_code, "en-us"])


def _set_initialize_ended_status(bus, status):
    bus.emit(Message("skills.initialize.ended"))
    status.set_ready()


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


def _wait_for_internet_connection():
    while not connected():
        time.sleep(1)


def shutdown(skill_manager, event_scheduler, status):
    LOG.info('Shutting down Skills service')
    status.set_stopping()
    if event_scheduler is not None:
        event_scheduler.shutdown()
    # Terminate all running threads that update skills
    if skill_manager is not None:
        skill_manager.stop()
        skill_manager.join()
    LOG.info('Skills service shutdown complete!')


if __name__ == "__main__":
    main()
