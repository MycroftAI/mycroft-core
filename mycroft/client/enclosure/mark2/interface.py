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
"""Define the enclosure interface for Mark II devices."""
import json
from threading import Timer
from time import sleep, time

from websocket import WebSocketApp

from mycroft.client.enclosure.base import Enclosure
from mycroft.messagebus.message import Message
from mycroft.util import create_daemon
from mycroft.util.log import LOG
from .display_bus import start_display_message_bus
from ..startup import EnclosureInternet


class EnclosureMark2(Enclosure):
    def __init__(self):
        LOG.info('Starting Mark 2 enclosure')
        super().__init__()
        self.display_bus_client = None
        self._define_event_handlers()
        self.finished_loading = False
        self.active_screen = 'loading'
        self.paused_screen = None
        self.active_until_stopped = set()
        self.internet = EnclosureInternet(self.bus, self.config)

    def _define_event_handlers(self):
        self.bus.on('display.bus.start', self.on_display_bus_start)
        self.bus.on('display.screen.show', self.on_display_screen_show)
        self.bus.on('display.screen.stop', self.on_display_screen_stop)
        self.bus.on('display.screen.update', self.on_display_screen_update)
        self.bus.on('enclosure.internet.connected', self.on_internet_connected)
        self.bus.on('enclosure.mouth.reset', self.reset_display)
        self.bus.on('enclosure.mouth.think', self.show_thinking_screen)
        self.bus.on('enclosure.mouth.viseme_list', self.show_generic_screen)
        self.bus.on('mycroft.audio.service.stop', self.on_display_screen_stop)
        self.bus.on('mycroft.intent.fallback.start', self.show_thinking_screen)
        self.bus.on('mycroft.ready', self.on_core_ready)
        self.bus.on('play:status', self.show_play_screen)

    def on_display_bus_start(self, _):
        """Start the display message bus."""
        websocket_config = self.global_config.get("gui_websocket")
        start_display_message_bus(websocket_config)
        self._connect_to_display_bus(websocket_config)
        self.internet.check_connection()

    def _connect_to_display_bus(self, websocket_config):
        """Connect to the display bus to send messages."""
        websocket_url = 'ws://{host}:{port}/display'.format(
            host=websocket_config['host'],
            port=websocket_config['base_port']
        )
        LOG.info('Connecting to display websocket on ' + websocket_url)
        self.display_bus_client = WebSocketApp(
            url=websocket_url,
            on_open=self.on_display_bus_open,
        )
        create_daemon(self.display_bus_client.run_forever)
        LOG.info('Display websocket client started successfully')

    def on_display_bus_open(self):
        """Let the display know that the display bus is ready."""
        LOG.info('Display message bus ready for connections')
        self.bus.emit(Message('display.bus.ready'))

    def on_core_ready(self, _):
        self._finish_screen('loading', wait_for_it=4)
        self._show_screen('splash')
        self.finished_loading = True
        Timer(7, self.show_idle).start()

    def show_idle(self):
        self.active_screen = None
        message = Message(msg_type='mycroft.device.show.idle')
        self.bus.emit(message)

    def on_display_screen_show(self, message):
        """Send a message to the display bus that will show a screen."""
        LOG.info('**** showing screen ' + message.data['screen_name'])
        LOG.info('**** currently displaying screen: ' + str(self.active_screen))
        if message.data['active_until_stopped']:
            self.active_until_stopped.add(message.data['screen_name'])
        self._show_screen(
            message.data['screen_name'],
            message.data.get('screen_data')
        )

    def _ignore_screen_show_request(self, screen_name):
        return (
            (screen_name == 'idle' and self.active_screen) or
            screen_name == self.paused_screen
        )

    def _show_screen(self, screen_name, screen_data=None):
        LOG.info('***** attempting to show screen ' + screen_name)
        LOG.info('***** active screen ' + str(self.active_screen) + 'data: ' + str(screen_data))
        ignore = self._ignore_screen_show_request(screen_name)
        if not ignore:
            if self.active_screen in self.active_until_stopped:
                if screen_name != self.active_screen:
                    self.paused_screen = self.active_screen
            self.active_screen = screen_name
            message_data = dict(screen_name=screen_name)
            if screen_data is not None:
                message_data.update(screen_data=screen_data)
            self._send_message_to_display_bus(
                message_type='display.screen.show',
                message_data=message_data
            )

    def reset_display(self, _):
        if self.finished_loading:
            if self.paused_screen is None:
                if self.active_screen not in self.active_until_stopped:
                    self.active_screen = None
            else:
                self.active_screen = self.paused_screen
                self.paused_screen = None

    def on_display_screen_update(self, message):
        self._send_message_to_display_bus(
            message_type='display.screen.update',
            message_data=message.data
        )

    def _send_message_to_display_bus(self, message_type, message_data):
        msg = dict(type=message_type, data=message_data)
        msg = json.dumps(msg)
        self.display_bus_client.send(msg)

    def on_display_screen_stop(self, _):
        sleep(5)
        self.show_idle()

    def show_generic_screen(self, message):
        """Display viseme for skills that do not otherwise use the display."""
        if self.active_screen in (None, 'thinking'):
            LOG.info('no displayed skill found, sending generic screen')
            self._show_screen(screen_name='generic', screen_data=message.data)
            self.active_screen = 'generic'

    def show_thinking_screen(self, _):
        self._show_screen(screen_name='thinking')
        self.active_screen = 'thinking'

    def show_play_screen(self, message):
        self.active_until_stopped.add('play')
        self._show_screen(screen_name='play', screen_data=message.data)

    def on_internet_connected(self, _):
        self._finish_screen(screen_name='loading', wait_for_it=4)
        self._show_screen('wifi_connected')
        sleep(2)
        screen_data = dict(loading_status='LOADING SKILLS')
        self._show_screen('loading', screen_data)

    def _finish_screen(self, screen_name, wait_for_it=None):
        self._send_message_to_display_bus(
            message_type='display.screen.finish',
            message_data=dict(screen_name=screen_name)
        )
        if wait_for_it is not None:
            sleep(wait_for_it)
