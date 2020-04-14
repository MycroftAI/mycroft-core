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
"""Define the web socket event handler for the message bus."""
import json
import sys
import traceback

from tornado.websocket import WebSocketHandler
from pyee import EventEmitter

from mycroft.messagebus.message import Message
from mycroft.util.log import LOG

client_connections = []


class MessageBusEventHandler(WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.emitter = EventEmitter()

    def on(self, event_name, handler):
        self.emitter.on(event_name, handler)

    def on_message(self, message):
        LOG.debug(message)
        try:
            deserialized_message = Message.deserialize(message)
        except Exception:
            return

        try:
            self.emitter.emit(deserialized_message.msg_type,
                              deserialized_message)
        except Exception as e:
            LOG.exception(e)
            traceback.print_exc(file=sys.stdout)
            pass

        for client in client_connections:
            client.write_message(message)

    def open(self):
        self.write_message(Message("connected").serialize())
        client_connections.append(self)

    def on_close(self):
        client_connections.remove(self)

    def emit(self, channel_message):
        if (hasattr(channel_message, 'serialize') and
                callable(getattr(channel_message, 'serialize'))):
            self.write_message(channel_message.serialize())
        else:
            self.write_message(json.dumps(channel_message))

    def check_origin(self, origin):
        return True
