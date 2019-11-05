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
from time import sleep

from websocket import WebSocketApp

import mycroft.dialog
from mycroft.api import has_been_paired
from mycroft.client.enclosure.base import Enclosure
from mycroft.messagebus.message import Message
from mycroft.util import connected, create_daemon, wait_while_speaking
from mycroft.util.log import LOG
from .display_bus import start_display_message_bus


class EnclosureMark2(Enclosure):
    def __init__(self):
        super().__init__()
        LOG.info('Starting Mark 2 enclosure')
        self.bus.on("display.bus.start", self.on_display_bus_start)
        self.bus.on("display.screen.show", self.on_display_show_screen)
        self.display_bus_client = None
        self._setup_internet_check()
        LOG.info('Mark 2 enclosure setup complete')

    def _setup_internet_check(self):
        """Set a timer thread to check for internet connectivity.

        Time is delayed this for several seconds to ensure that the speech
        client is up and connected to the message bus, allowing it to
        receive the "speak" event.
        """
        Timer(5, self._check_for_internet).start()

    def on_display_bus_start(self, _):
        """Start the display message bus."""
        websocket_config = self.global_config.get("gui_websocket")
        start_display_message_bus(websocket_config)
        self._connect_to_display_bus(websocket_config)

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
            on_message=self.on_display_bus_message
        )
        create_daemon(self.display_bus_client.run_forever)
        LOG.info('Display websocket client started successfully')

    def on_display_bus_open(self):
        """Let the display know that the display bus is ready."""
        LOG.info('Display message bus ready for connections')
        self.bus.emit(Message('display.bus.ready'))

    def on_display_bus_message(self, message):
        LOG.info('Receiving a message...')
        try:
            LOG.info('Client received message: ' + message)
        except Exception:
            LOG.exception('failed to receive message')

    def on_display_show_screen(self, message):
        """Send a message to the display bus that will show a screen."""
        msg = dict(type=message.msg_type, data=message.data)
        msg = json.dumps(msg)
        self.display_bus_client.send(msg)

    def _check_for_internet(self):
        """Run wifi setup if an internet connection is not established."""
        LOG.info("Checking internet connection")
        if connected():
            LOG.info('Enclosure is connected to internet')
            self.bus.emit(Message(msg_type='enclosure.internet.connected'))
        else:
            LOG.info('no internet connection detected; starting wifi setup')
            self._mute_microphone()
            if not has_been_paired():
                self.bus.once('mycroft.paired', self._unmute_mike)
                self._speak_intro()
            else:
                self.bus.once(
                    'enclosure.internet.connected',
                    self._unmute_mike
                )
            self._start_wifi_setup()
            self._wait_for_internet_connection()
            self.bus.emit(Message(msg_type='enclosure.internet.connected'))

    def _mute_microphone(self):
        """Mute the microphone while wifi setup is running."""
        message = Message("mycroft.mic.mute")
        self.bus.emit(message)

    def _speak_intro(self):
        """Send a message to the bus triggering the introduction dialog."""
        message = Message(
            msg_type='speak',
            data=dict(utterance=mycroft.dialog.get('mycroft.intro'))
        )
        self.bus.emit(message)
        wait_while_speaking()
        sleep(2)  # a pause sounds better than just jumping in

    def _start_wifi_setup(self):
        """Send a message to the bus that will start the wifi setup process."""
        message = Message(
            msg_type='system.wifi.setup',
            data=dict(allow_timeout=False, lang=self.lang)
        )
        self.bus.emit(message)

    @staticmethod
    def _wait_for_internet_connection():
        while not connected():
            sleep(1)

    def _unmute_mike(self, _):
        """Turn microphone back on after the pairing is complete."""
        self.bus.emit(Message("mycroft.mic.unmute"))
