# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import json
import time
from multiprocessing.pool import ThreadPool

from pyee import EventEmitter
from websocket import WebSocketApp

import mycroft.util.log
from mycroft.configuration.config import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.util import str2bool

__author__ = 'seanfitz'

logger = mycroft.util.log.getLogger(__name__)

config = ConfigurationManager.get()
client_config = config.get("messagebus_client")


class WebsocketClient(object):
    def __init__(self, host=client_config.get("host"),
                 port=client_config.get("port"),
                 path=client_config.get("route"),
                 ssl=str2bool(client_config.get("ssl"))):
        self.emitter = EventEmitter()
        self.scheme = "wss" if ssl else "ws"
        self.host = host
        self.port = port
        self.path = path
        self.exp_backoff_counter = 1
        self.client = self._create_new_connection()
        self.pool = ThreadPool(10)

    def _create_new_connection(self):
        return WebSocketApp(
            self.scheme + "://" + self.host + ":" + str(self.port) + self.path,
            on_open=self.on_open,
            on_close=self.on_close,
            on_error=self.on_error,
            on_message=self.on_message)

    def on_open(self, ws):
        logger.info("Connected")
        self.emitter.emit("open")

    def on_close(self, ws):
        self.emitter.emit("close")

    def on_error(self, ws, error):
        try:
            self.emitter.emit('error', error)
            self.client.close()
        except Exception, e:
            logger.error(repr(e))
        sleep_time = self.exp_backoff_counter
        logger.warn(
            "Disconnecting on error, reconnecting in %d seconds." % sleep_time)
        self.exp_backoff_counter = min(self.exp_backoff_counter * 2, 60)
        time.sleep(sleep_time)
        self.client = self._create_new_connection()
        self.run_forever()

    def on_message(self, ws, message):
        self.emitter.emit('message', message)
        parsed_message = Message.deserialize(message)
        self.pool.apply_async(
            self.emitter.emit, (parsed_message.message_type, parsed_message))

    def emit(self, message):
        if (not self.client or not self.client.sock or
                not self.client.sock.connected):
            return
        if hasattr(message, 'serialize'):
            self.client.send(message.serialize())
        else:
            self.client.send(json.dumps(message.__dict__))

    def on(self, event_name, func):
        self.emitter.on(event_name, func)

    def once(self, event_name, func):
        self.emitter.once(event_name, func)

    def remove(self, event_name, func):
        self.emitter.remove_listener(event_name, func)

    def run_forever(self):
        self.client.run_forever()

    def close(self):
        self.client.close()


def echo():
    client = WebsocketClient()

    def echo(message):
        logger.info(message)

    def repeat_utterance(message):
        message.message_type = 'speak'
        client.emit(message)
    client.on('message', echo)
    client.on('recognizer_loop:utterance', repeat_utterance)
    client.run_forever()

if __name__ == "__main__":
    echo()
