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
from threading import Event, Lock
from time import sleep, monotonic

from msm import MycroftSkillsManager
from mycroft.audio import wait_while_speaking
from mycroft.messagebus.client import MessageBusClient
from mycroft.messagebus import Message
from mycroft.util import create_daemon


class InterceptAllBusClient(MessageBusClient):
    def __init__(self):
        super().__init__()
        self.messages = []
        self.message_lock = Lock()

    def on_message(self, message):
        with self.message_lock:
            self.messages.append(Message.deserialize(message))
        super().on_message(message)

    def get_messages(self, msg_type):
        with self.message_lock:
            if msg_type is None:
                return [m for m in self.messages]
            else:
                return [m for m in self.messages if m.msg_type == msg_type]

    def clear_messages(self):
        with self.message_lock:
            self.messages = []


def before_all(context):
    bus = InterceptAllBusClient()
    bus_connected = Event()
    bus.once('open', bus_connected.set)

    create_daemon(bus.run_forever)

    context.msm = MycroftSkillsManager()
    # Wait for connection
    print('Waiting for messagebus connection...')
    bus_connected.wait()

    print('Waiting for skills to be loaded...')
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
    context.matched_message = None


def after_all(context):
    context.bus.close()


def after_feature(context, feature):
    sleep(2)


def after_scenario(context, scenario):
    # TODO wait for skill handler complete
    sleep(0.5)
    wait_while_speaking()
    context.bus.clear_messages()
    context.matched_message = None
    sleep(0.5)
