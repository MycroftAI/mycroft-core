# Copyright 2022 Mycroft AI Inc.
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
"""GUI message bus implementation

The basic mechanism is:
    1) GUI client connects to the core messagebus
    2) Core prepares a port for a socket connection to this GUI
    3) The availability of the port is sent over the Core
    4) The GUI connects to the GUI message bus websocket
    5) Connection persists for graphical interaction indefinitely

If the connection is lost, it must be renegotiated and restarted.
"""
import asyncio
import json
from threading import Lock

from tornado import ioloop
from tornado.options import parse_command_line
from tornado.web import Application
from tornado.websocket import WebSocketHandler

from mycroft.configuration import Configuration
from mycroft.messagebus import Message
from mycroft.util.log import LOG
from mycroft.util.process_utils import create_daemon

write_lock = Lock()


def get_gui_websocket_config():
    """Retrieves the configuration values for establishing a GUI message bus"""
    config = Configuration.get()
    websocket_config = config["gui_websocket"]

    return websocket_config


def create_gui_service(enclosure) -> Application:
    """Initiate a websocket for communicating with the GUI service."""
    LOG.info('Starting message bus for GUI...')
    websocket_config = get_gui_websocket_config()
    # Disable all tornado logging so mycroft loglevel isn't overridden
    parse_command_line(['--logging=None'])

    routes = [(websocket_config['route'], GUIWebsocketHandler)]
    application = Application(routes, debug=True)
    application.enclosure = enclosure
    application.listen(
        websocket_config['base_port'], websocket_config['host']
    )

    create_daemon(ioloop.IOLoop.instance().start)
    LOG.info('GUI Message bus started!')
    return application


def send_message_to_gui(message):
    """Sends the supplied message to all connected GUI clients."""
    for connection in GUIWebsocketHandler.clients:
        try:
            connection.send(message)
        except Exception as e:
            LOG.exception(repr(e))


def determine_if_gui_connected():
    """Returns True if any clients are connected to the GUI bus."""
    return len(GUIWebsocketHandler.clients) > 0


class GUIWebsocketHandler(WebSocketHandler):
    """Defines the websocket pipeline between the GUI and Mycroft."""
    clients = []

    def open(self):
        GUIWebsocketHandler.clients.append(self)
        LOG.info('New Connection opened!')
        self.synchronize()

    def on_close(self):
        LOG.info('Closing {}'.format(id(self)))
        GUIWebsocketHandler.clients.remove(self)

    def synchronize(self):
        """ Upload namespaces, pages and data to the last connected. """
        namespace_pos = 0
        enclosure = self.application.enclosure

        for namespace in enclosure.active_namespaces:
            LOG.info(f'Sync {namespace.name}')
            # Insert namespace
            self.send({"type": "mycroft.session.list.insert",
                       "namespace": "mycroft.system.active_skills",
                       "position": namespace_pos,
                       "data": [{"skill_id": namespace.name}]
                       })
            # Insert pages
            self.send({"type": "mycroft.gui.list.insert",
                       "namespace": namespace.name,
                       "position": 0,
                       "data": [{"url": p.url} for p in namespace.pages]
                       })
            # Insert data
            for key, value in namespace.data.items():
                self.send({"type": "mycroft.session.set",
                           "namespace": namespace.name,
                           "data": {key: value}
                           })
            namespace_pos += 1

    def on_message(self, message):
        LOG.info("Received: {message}")
        msg = json.loads(message)
        if (msg.get('type') == "mycroft.events.triggered" and
                (msg.get('event_name') == 'page_gained_focus' or
                    msg.get('event_name') == 'system.gui.user.interaction')):
            # System event, a page was changed
            event_name = msg.get('event_name')
            if event_name == 'page_gained_focus':
                msg_type = 'gui.page_gained_focus'
            else:
                msg_type = 'gui.page_interaction'

            msg_data = {'namespace': msg['namespace'],
                        'page_number': msg['parameters'].get('number'),
                        'skill_id': msg['parameters'].get('skillId')}
        elif msg.get('type') == "mycroft.events.triggered":
            # A normal event was triggered
            msg_type = '{}.{}'.format(msg['namespace'], msg['event_name'])
            msg_data = msg['parameters']

        elif msg.get('type') == 'mycroft.session.set':
            # A value was changed send it back to the skill
            msg_type = '{}.{}'.format(msg['namespace'], 'set')
            msg_data = msg['data']

        message = Message(msg_type, msg_data)
        LOG.info('Forwarding to bus...')
        self.application.enclosure.core_bus.emit(message)
        LOG.info('Done!')

    def write_message(self, *arg, **kwarg):
        """Wraps WebSocketHandler.write_message() with a lock. """
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        with write_lock:
            super().write_message(*arg, **kwarg)

    def send(self, data):
        """Send the given data across the socket as JSON

        Args:
            data (dict): Data to transmit
        """
        s = json.dumps(data)
        #LOG.info('Sending {}'.format(s))
        self.write_message(s)

    def check_origin(self, origin):
        """Disable origin check to make js connections work."""
        return True
