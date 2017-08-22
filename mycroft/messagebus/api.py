from mycroft.messagebus.message import Message
import time

__author__ = "jarbas"


class BusQuery():
    def __init__(self, emitter, name, message_data=None, message_context=None):
        self.emitter = emitter
        self.name = name
        if message_data is None:
            message_data = {}
        if message_context is None:
            message_context = {}
        self.data = message_data
        self.context = message_context
        self.waiting = False
        self.response = Message(None, None, None)

    def _end_wait(self, message):
        self.response = message
        self.waiting = False

    def _wait_response(self, timeout):
        start = time.time()
        elapsed = 0
        self.waiting = True
        while self.waiting and elapsed < timeout:
            elapsed = time.time() - start
            time.sleep(0.1)
        self.waiting = False

    def send(self, response_type=None, timeout=10):
        if response_type is None:
            response_type = self.name + ".reply"
        self.emitter.on(response_type, self._end_wait)
        self.emitter.emit(Message(self.name, self.data, self.context))
        self._wait_response(timeout)
        return self.response.data

    def get_response_type(self):
        return self.response.type

    def get_response_data(self):
        return self.response.data

    def get_response_context(self):
        return self.response.context


class BusResponder():
    def __init__(self, emitter, response_type, response_data=None,
                 response_context=None, trigger_messages=None):
        self.emitter = emitter
        if response_data is None:
            response_data = {}
        if response_context is None:
            response_context = {}
        if trigger_messages is None:
            trigger_messages = []
        self.response_type = response_type
        self.response_data = response_data
        self.response_context = response_context
        for message_type in trigger_messages:
            self.listen(message_type)

    def listen(self, message_type):
        self.emitter.on(message_type, self._respond)

    def update_response(self, data=None, context=None):
        if data is not None:
            self.response_data = data
        if context is not None:
            self.response_context = context

    def _respond(self, message):
        self.emitter.emit(Message(self.response_type, self.response_data,
                                  self.response_context))
