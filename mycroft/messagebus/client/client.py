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
import json
import time
import traceback
from threading import Event

from websocket import (
    WebSocketApp,
    WebSocketConnectionClosedException,
    WebSocketException
)

from mycroft.messagebus.load_config import load_message_bus_config
from mycroft.messagebus.message import Message
from mycroft.util import create_echo_function
from mycroft.util.log import LOG
from .threaded_event_emitter import ThreadedEventEmitter


class MessageBusClient:
    def __init__(self, host=None, port=None, route=None, ssl=None):
        config_overrides = dict(host=host, port=port, route=route, ssl=ssl)
        self.config = load_message_bus_config(**config_overrides)
        self.emitter = ThreadedEventEmitter()
        self.client = self.create_client()
        self.retry = 5
        self.connected_event = Event()
        self.started_running = False

    @staticmethod
    def build_url(host, port, route, ssl):
        return '{scheme}://{host}:{port}{route}'.format(
            scheme='wss' if ssl else 'ws',
            host=host,
            port=str(port),
            route=route)

    def create_client(self):
        url = MessageBusClient.build_url(
            ssl=self.config.ssl,
            host=self.config.host,
            port=self.config.port,
            route=self.config.route
        )
        return WebSocketApp(
            url,
            on_open=self.on_open,
            on_close=self.on_close,
            on_error=self.on_error,
            on_message=self.on_message
        )

    def on_open(self):
        LOG.info("Connected")
        self.connected_event.set()
        self.emitter.emit("open")
        # Restore reconnect timer to 5 seconds on sucessful connect
        self.retry = 5

    def on_close(self):
        self.emitter.emit("close")

    def on_error(self, error):
        """ On error start trying to reconnect to the websocket. """
        if isinstance(error, WebSocketConnectionClosedException):
            LOG.warning('Could not send message because connection has closed')
        else:
            LOG.exception('=== ' + repr(error) + ' ===')

        try:
            self.emitter.emit('error', error)
            if self.client.keep_running:
                self.client.close()
        except Exception as e:
            LOG.error('Exception closing websocket: ' + repr(e))

        LOG.warning(
            "Message Bus Client will reconnect in %d seconds." % self.retry
        )
        time.sleep(self.retry)
        self.retry = min(self.retry * 2, 60)
        try:
            self.emitter.emit('reconnecting')
            self.client = self.create_client()
            self.run_forever()
        except WebSocketException:
            pass

    def on_message(self, message):
        parsed_message = Message.deserialize(message)
        self.emitter.emit('message', message)
        self.emitter.emit(parsed_message.msg_type, parsed_message)

    def emit(self, message):
        if not self.connected_event.wait(10):
            if not self.started_running:
                raise ValueError('You must execute run_forever() '
                                 'before emitting messages')
            self.connected_event.wait()

        try:
            if hasattr(message, 'serialize'):
                self.client.send(message.serialize())
            else:
                self.client.send(json.dumps(message.__dict__))
        except WebSocketConnectionClosedException:
            LOG.warning('Could not send {} message because connection '
                        'has been closed'.format(message.msg_type))

    def wait_for_response(self, message, reply_type=None, timeout=None):
        """Send a message and wait for a response.

        Args:
            message (Message): message to send
            reply_type (str): the message type of the expected reply.
                              Defaults to "<message.msg_type>.response".
            timeout: seconds to wait before timeout, defaults to 3
        Returns:
            The received message or None if the response timed out
        """
        response = []

        def handler(message):
            """Receive response data."""
            response.append(message)

        # Setup response handler
        self.once(reply_type or message.msg_type + '.response', handler)
        # Send request
        self.emit(message)
        # Wait for response
        start_time = time.monotonic()
        while len(response) == 0:
            time.sleep(0.2)
            if time.monotonic() - start_time > (timeout or 3.0):
                try:
                    self.remove(reply_type, handler)
                except (ValueError, KeyError):
                    # ValueError occurs on pyee 1.0.1 removing handlers
                    # registered with once.
                    # KeyError may theoretically occur if the event occurs as
                    # the handler is removed
                    pass
                return None
        return response[0]

    def on(self, event_name, func):
        self.emitter.on(event_name, func)

    def once(self, event_name, func):
        self.emitter.once(event_name, func)

    def remove(self, event_name, func):
        try:
            if event_name in self.emitter._events:
                LOG.debug("Removing found '"+str(event_name)+"'")
            else:
                LOG.debug("Not able to find '"+str(event_name)+"'")
            self.emitter.remove_listener(event_name, func)
        except ValueError:
            LOG.warning('Failed to remove event {}: {}'.format(event_name,
                                                               str(func)))
            for line in traceback.format_stack():
                LOG.warning(line.strip())

            if event_name in self.emitter._events:
                LOG.debug("Removing found '"+str(event_name)+"'")
            else:
                LOG.debug("Not able to find '"+str(event_name)+"'")
            LOG.warning("Existing events: " + str(self.emitter._events))
            for evt in self.emitter._events:
                LOG.warning("   "+str(evt))
                LOG.warning("       "+str(self.emitter._events[evt]))
            if event_name in self.emitter._events:
                LOG.debug("Removing found '"+str(event_name)+"'")
            else:
                LOG.debug("Not able to find '"+str(event_name)+"'")
            LOG.warning('----- End dump -----')

    def remove_all_listeners(self, event_name):
        '''
            Remove all listeners connected to event_name.

            Args:
                event_name: event from which to remove listeners
        '''
        if event_name is None:
            raise ValueError
        self.emitter.remove_all_listeners(event_name)

    def run_forever(self):
        self.started_running = True
        self.client.run_forever()

    def close(self):
        self.client.close()
        self.connected_event.clear()


def echo():
    message_bus_client = MessageBusClient()

    def repeat_utterance(message):
        message.msg_type = 'speak'
        message_bus_client.emit(message)

    message_bus_client.on('message', create_echo_function(None))
    message_bus_client.on('recognizer_loop:utterance', repeat_utterance)
    message_bus_client.run_forever()


if __name__ == "__main__":
    echo()
