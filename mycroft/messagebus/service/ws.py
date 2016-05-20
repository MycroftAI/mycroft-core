import traceback
import sys
import json

from pyee import EventEmitter
import tornado.websocket

from mycroft.messagebus.message import Message
import mycroft.util.log

logger = mycroft.util.log.getLogger(__name__)
__author__ = 'seanfitz'

EventBusEmitter = EventEmitter()

client_connections = []


class WebsocketEventHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        tornado.websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
        self.emitter = EventBusEmitter

    def on(self, event_name, handler):
        self.emitter.on(event_name, handler)

    def on_message(self, message):
        logger.debug(message)
        try:
            deserialized_message = Message.deserialize(message)
        except:
            return

        try:
            self.emitter.emit(deserialized_message.message_type, deserialized_message)
        except Exception, e:
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
        if hasattr(channel_message, 'serialize') and callable(getattr(channel_message, 'serialize')):
            self.write_message(channel_message.serialize())
        else:
            self.write_message(json.dumps(channel_message))
