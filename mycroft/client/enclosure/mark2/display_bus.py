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
"""Message bus for a Mark II display."""

from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.websocket import WebSocketHandler

from mycroft.util import create_daemon
from mycroft.util.log import LOG


def start_display_message_bus(websocket_config):
    """Message traffic between core and display will use a separate bus."""
    LOG.info("Starting display message bus websocket...")
    try:
        display_message_handler = ('/display', DisplayMessageBus)
        display_message_bus = Application(
            handlers=[display_message_handler]
        )
        display_message_bus.listen(
            websocket_config['base_port'],
            websocket_config['host']
        )
    except Exception:
        LOG.exception('Error creating display application')
    else:
        LOG.info("Display message bus websocket started successfully.")
    create_daemon(IOLoop.current().start)


class DisplayMessageBus(WebSocketHandler):
    connections = set()

    def open(self):
        LOG.info('New connection to display event server open')
        self.connections.add(self)

    def on_message(self, message):
        for connection in self.connections:
            connection.write_message(message)

    def on_close(self):
        LOG.info('Display event handler closed')
