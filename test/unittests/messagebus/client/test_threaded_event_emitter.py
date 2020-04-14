# Copyright 2019 Mycroft AI Inc.
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
from time import sleep

from mycroft import Message
from mycroft.messagebus.client.threaded_event_emitter import \
    ThreadedEventEmitter


class TestThreadedEventEmitter:
    def setup(self):
        self.emitter = ThreadedEventEmitter()
        self.count = 0
        self.msg = Message('testing')

    def example_event(self, message):
        self.count += 1

    def test_on(self):
        self.emitter.on(self.msg.msg_type, self.example_event)
        self.emitter.emit(self.msg.msg_type, self.msg)
        self.emitter.emit(self.msg.msg_type, self.msg)
        sleep(0.1)
        assert self.count == 2

    def test_once(self):
        self.emitter.once(self.msg.msg_type, self.example_event)
        self.emitter.emit(self.msg.msg_type, self.msg)
        self.emitter.emit(self.msg.msg_type, self.msg)
        sleep(0.1)
        assert self.count == 1

    def test_remove_listener_on(self):
        self.emitter.on(self.msg.msg_type, self.example_event)
        self.emitter.remove_listener(self.msg.msg_type, self.example_event)
        self.emitter.emit(self.msg.msg_type)
        sleep(0.1)
        assert self.count == 0

    def test_remove_all_listeners(self):
        self.emitter.on(self.msg.msg_type, self.example_event)
        self.emitter.once(self.msg.msg_type, self.example_event)
        self.emitter.remove_all_listeners(self.msg.msg_type)
        self.emitter.emit(self.msg.msg_type)
        sleep(0.1)
        assert self.count == 0
