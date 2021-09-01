# Copyright 2020 Mycroft AI Inc.
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
import logging
from threading import Event, Lock
from time import sleep, monotonic
from behave.contrib.scenario_autoretry import patch_scenario_with_autoretry

from msm import MycroftSkillsManager
from mycroft.audio import wait_while_speaking
from mycroft.configuration import Configuration
from mycroft.messagebus.client import MessageBusClient
from mycroft.messagebus import Message
from mycroft.util import create_daemon


def create_voight_kampff_logger():
    fmt = logging.Formatter('{asctime} | {name} | {levelname} | {message}',
                            style='{')
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    log = logging.getLogger('Voight Kampff')
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    return log


class InterceptAllBusClient(MessageBusClient):
    """Bus Client storing all messages received.

    This allows read back of older messages and non-event-driven operation.
    """
    def __init__(self):
        super().__init__()
        self.messages = []
        self.message_lock = Lock()
        self.new_message_available = Event()
        self._processed_messages = 0

    def on_message(self, message):
        """Extends normal operation by storing the received message.

        Args:
            message (Message): message from the Mycroft bus
        """
        with self.message_lock:
            self.messages.append(Message.deserialize(message))
        self.new_message_available.set()
        super().on_message(message)

    def get_messages(self, msg_type):
        """Get messages from received list of messages.

        Args:
            msg_type (None,str): string filter for the message type to extract.
                                 if None all messages will be returned.
        """
        with self.message_lock:
            self._processed_messages = len(self.messages)
            if msg_type is None:
                return [m for m in self.messages]
            else:
                return [m for m in self.messages if m.msg_type == msg_type]

    def remove_message(self, msg):
        """Remove a specific message from the list of messages.

        Args:
            msg (Message): message to remove from the list
        """
        with self.message_lock:
            if msg not in self.messages:
                raise ValueError(f'{msg} was not found in '
                                 'the list of messages.')
            # Update processed message count if a read message was removed
            if self.messages.index(msg) < self._processed_messages:
                self._processed_messages -= 1

            self.messages.remove(msg)

    def clear_messages(self):
        """Clear all messages that has been fetched at least once."""
        with self.message_lock:
            self.messages = self.messages[self._processed_messages:]
            self._processed_messages = 0

    def clear_all_messages(self):
        """Clear all messages."""
        with self.message_lock:
            self.messages = []
            self._processed_messages = 0


def before_all(context):
    log = create_voight_kampff_logger()
    bus = InterceptAllBusClient()
    bus_connected = Event()
    bus.once('open', bus_connected.set)

    create_daemon(bus.run_forever)

    context.msm = MycroftSkillsManager()
    # Wait for connection
    log.info('Waiting for messagebus connection...')
    bus_connected.wait()

    log.info('Waiting for skills to be loaded...')
    start = monotonic()
    while True:
        response = bus.wait_for_response(Message('mycroft.skills.all_loaded'))
        if response and response.data['status']:
            break
        elif monotonic() - start >= 2 * 60:
            raise Exception('Timeout waiting for skills to become ready.')
        else:
            sleep(1)

    context.bus = bus
    context.step_timeout = 10  # Reset the step_timeout to 10 seconds
    context.matched_message = None
    context.log = log
    context.config = Configuration.get()
    Configuration.set_config_update_handlers(bus)


def before_feature(context, feature):
    context.log.info('Starting tests for {}'.format(feature.name))
    for scenario in feature.scenarios:
        patch_scenario_with_autoretry(scenario, max_attempts=2)


def after_all(context):
    context.bus.close()


def after_feature(context, feature):
    context.log.info('Result: {} ({:.2f}s)'.format(str(feature.status.name),
                                                   feature.duration))


def after_scenario(context, scenario):
    """Wait for mycroft completion and reset any changed state."""
    # TODO wait for skill handler complete
    wait_while_speaking()
    context.bus.clear_all_messages()
    context.matched_message = None
    context.step_timeout = 10  # Reset the step_timeout to 10 seconds
