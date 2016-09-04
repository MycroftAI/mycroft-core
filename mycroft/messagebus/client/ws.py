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

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.util import validate_param
from mycroft.util.log import getLogger

__author__ = 'seanfitz', 'jdorleans'

LOG = getLogger(__name__)
config = ConfigurationManager.get().get("websocket")


class WebsocketClient(object):
    def __init__(self, host=config.get("host"), port=config.get("port"),
                 route=config.get("route"), ssl=config.get("ssl")):

        validate_param(host, "websocket.host")
        validate_param(port, "websocket.port")
        validate_param(route, "websocket.route")

        self.build_url(host, port, route, ssl)
        self.emitter = EventEmitter()
        self.client = self.create_client()
        self.pool = ThreadPool(10)
        self.retry = 1

    def build_url(self, host, port, route, ssl):
        scheme = "wss" if ssl else "ws"
        self.url = scheme + "://" + host + ":" + str(port) + route

    def create_client(self):
        return WebSocketApp(self.url,
                            on_open=self.on_open, on_close=self.on_close,
                            on_error=self.on_error, on_message=self.on_message)

    def on_open(self, ws):
        LOG.info("Connected")
        self.emitter.emit("open")

    def on_close(self, ws):
        self.emitter.emit("close")

    def on_error(self, ws, error):
        try:
            self.emitter.emit('error', error)
            self.client.close()
        except Exception, e:
            LOG.error(repr(e))
        LOG.warn("WS Client Error: reconnecting in %d seconds." % self.retry)
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
        LOG.info(message)

    def repeat_utterance(message):
        message.type = 'speak'
        client.emit(message)

    client.on('message', echo)
    client.on('recognizer_loop:utterance', repeat_utterance)
    client.run_forever()


if __name__ == "__main__":
    echo()
