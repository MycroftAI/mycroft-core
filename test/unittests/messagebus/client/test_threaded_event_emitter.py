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
        self.emitter.on(self.msg.type, self.example_event)
        self.emitter.emit(self.msg.type, self.msg)
        self.emitter.emit(self.msg.type, self.msg)
        sleep(0.1)
        assert self.count == 2

    def test_once(self):
        self.emitter.once(self.msg.type, self.example_event)
        self.emitter.emit(self.msg.type, self.msg)
        self.emitter.emit(self.msg.type, self.msg)
        sleep(0.1)
        assert self.count == 1

    def test_remove_listener_on(self):
        self.emitter.on(self.msg.type, self.example_event)
        self.emitter.remove_listener(self.msg.type, self.example_event)
        self.emitter.emit(self.msg.type)
        sleep(0.1)
        assert self.count == 0

    def test_remove_all_listeners(self):
        self.emitter.on(self.msg.type, self.example_event)
        self.emitter.once(self.msg.type, self.example_event)
        self.emitter.remove_all_listeners(self.msg.type)
        self.emitter.emit(self.msg.type)
        sleep(0.1)
        assert self.count == 0
