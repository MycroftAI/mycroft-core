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
import json
import time
from multiprocessing.pool import ThreadPool
from threading import Event

import monotonic
from pyee import EventEmitter
from websocket import WebSocketApp, WebSocketConnectionClosedException

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util import validate_param, create_echo_function
from mycroft.util.log import LOG


class WebsocketClient(object):
    def __init__(self, host=None, port=None, route=None, ssl=None):

        config = Configuration.get().get("websocket")
        host = host or config.get("host")
        port = port or config.get("port")
        route = route or config.get("route")
        ssl = ssl or config.get("ssl")
        validate_param(host, "websocket.host")
        validate_param(port, "websocket.port")
        validate_param(route, "websocket.route")

        self.url = WebsocketClient.build_url(host, port, route, ssl)
        self.emitter = EventEmitter()
        self.client = self.create_client()
        self.pool = ThreadPool(10)
        self.retry = 5
        self.connected_event = Event()
        self.started_running = False

    @staticmethod
    def build_url(host, port, route, ssl):
        scheme = "wss" if ssl else "ws"
        return scheme + "://" + host + ":" + str(port) + route

    def create_client(self):
        return WebSocketApp(self.url,
                            on_open=self.on_open, on_close=self.on_close,
                            on_error=self.on_error, on_message=self.on_message)

    def on_open(self, ws):
        LOG.info("Connected")
        self.connected_event.set()
        self.emitter.emit("open")
        # Restore reconnect timer to 5 seconds on sucessful connect
        self.retry = 5

    def on_close(self, ws):
        self.emitter.emit("close")

    def on_error(self, ws, error):
        if isinstance(error, WebSocketConnectionClosedException):
            LOG.warning('Could not send message because connection has closed')
            return

        LOG.exception(
            '=== ' + error.__class__.__name__ + ': ' + str(error) + ' ===')

        try:
            self.emitter.emit('error', error)
            if self.client.keep_running:
                self.client.close()
        except Exception as e:
            LOG.error('Exception closing websocket: ' + repr(e))
        LOG.warning("WS Client will reconnect in %d seconds." % self.retry)
        time.sleep(self.retry)
        self.retry = min(self.retry * 2, 60)
        self.client = self.create_client()
        self.run_forever()

    def on_message(self, ws, message):
        self.emitter.emit('message', message)
        parsed_message = Message.deserialize(message)
        self.pool.apply_async(
            self.emitter.emit, (parsed_message.type, parsed_message))

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
                        'has been closed'.format(message.type))

    def wait_for_response(self, message, reply_type=None, timeout=None):
        """Send a message and wait for a response.

        Args:
            message (Message): message to send
            reply_type (str): the message type of the expected reply.
                              Defaults to "<message.type>.response".
            timeout: seconds to wait before timeout, defaults to 3
        Returns:
            The received message or None if the response timed out
        """
        response = []

        def handler(message):
            """Receive response data."""
            response.append(message)

        # Setup response handler
        self.once(reply_type or message.type + '.response', handler)
        # Send request
        self.emit(message)
        # Wait for response
        start_time = monotonic.monotonic()
        while len(response) == 0:
            time.sleep(0.2)
            if monotonic.monotonic() - start_time > (timeout or 3.0):
                try:
                    self.remove(reply_type, handler)
                except (ValueError, KeyError):
                    # ValueError occurs on pyee 1.0.1 removing handlers
                    # registered with once.
                    # KeyError may theoretically occur if the event occurs as
                    # the handler is removbed
                    pass
                return None
        return response[0]

    def on(self, event_name, func):
        self.emitter.on(event_name, func)

    def once(self, event_name, func):
        self.emitter.once(event_name, func)

    def remove(self, event_name, func):
        try:
            self.emitter.remove_listener(event_name, func)
        except ValueError as e:
            LOG.warning('Failed to remove event {}: {}'.format(event_name, e))

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
    ws = WebsocketClient()

    def repeat_utterance(message):
        message.type = 'speak'
        ws.emit(message)

    ws.on('message', create_echo_function(None))
    ws.on('recognizer_loop:utterance', repeat_utterance)
    ws.run_forever()


if __name__ == "__main__":
    echo()
