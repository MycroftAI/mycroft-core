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

from mycroft.client.enclosure.base import Enclosure
from mycroft.messagebus.message import Message
from mycroft.util import create_daemon
from mycroft.util.log import LOG
from .display_bus import start_display_message_bus
from ..startup import EnclosureInternet
from mycroft.enclosure.hardware_enclosure import HardwareEnclosure


class EnclosureMark2(Enclosure):
    def __init__(self):
        LOG.debug('** Starting Mark2 enclosure (interface.py) **')
        super().__init__()
        self.display_bus_client = None
        self._define_event_handlers()
        self.finished_loading = False
        self.active_screen = 'loading'
        self.paused_screen = None
        self.is_pairing = False
        self.active_until_stopped = None

        self.internet = EnclosureInternet(self.bus, self.global_config)

        self.system_volume = 0.5   # pulse audio master system volume
        # if you want to do anything with the system volume
        # (ala pulseaudio, etc) do it here!
        self.hardware_volume = 0.5 # hardware/board level volume

        self.m2enc = HardwareEnclosure("Mark2", "xmos_volume_gpio_switches_xmos_leds")

        LOG.debug('** Ending Mark2 enclosure init (interface.py) **')


    def _define_event_handlers(self):
        """Assign methods to act upon message bus events."""
        self.bus.on('display.bus.start', self.on_display_bus_start)
        self.bus.on('display.screen.show', self.on_display_screen_show)
        self.bus.on('display.screen.update', self.on_display_screen_update)
        self.bus.on('display.screen.stop', self.on_display_screen_stop)
        self.bus.on('enclosure.internet.connected', self.on_internet_connected)
        self.bus.on('enclosure.mouth.reset', self.reset_display)
        self.bus.on('enclosure.mouth.think', self.show_thinking_screen)
        self.bus.on('enclosure.mouth.viseme_list', self.show_generic_screen)
        self.bus.on('mycroft.intent.fallback.start', self.show_thinking_screen)
        self.bus.on('mycroft.pairing.start', self.start_pairing)
        self.bus.on('mycroft.pairing.success', self.handle_paired)
        self.bus.on('mycroft.ready', self.on_core_ready)
        self.bus.on('mycroft.stop', self.on_display_screen_stop)
        self.bus.on('play:start', self.handle_play_start)
        self.bus.on('play:status', self.show_play_screen)
        self.bus.on('system.wifi.ap_up', self.handle_access_point_up)
        self.bus.on(
            'system.wifi.ap_device_connected',
            self.handle_access_point_connected
        )
        self.bus.on('mycroft.volume.set', self.on_volume_set)
        self.bus.on('mycroft.volume.get', self.on_volume_get)
        self.bus.on('mycroft.volume.duck', self.on_volume_duck)
        self.bus.on('mycroft.volume.unduck', self.on_volume_unduck)


    def on_volume_duck(self, message):
        LOG.warning("Mark2 volume duck deprecated! use volume set instead.")

    def on_volume_unduck(self, message):
        LOG.warning("Mark2 volume unduck deprecated! use volume set instead.")

    def on_volume_set(self, message):
        self.hardware_volume = message.data.get("percent", self.hardware_volume)
        self.m2enc.hardware_volume.set_hw_volume(self.hardware_volume)

    def on_volume_get(self, message):
        self.bus.emit(message.response(data={'percent': self.hardware_volume, 'muted': False}))

    def on_display_bus_start(self, _):
        """Start the display message bus."""
        websocket_config = self.global_config.get("gui_websocket")
        start_display_message_bus(websocket_config)
        self._connect_to_display_bus(websocket_config)
        self.internet.check_connection()

    def _connect_to_display_bus(self, websocket_config):
        try:
            """Connect to the display bus to send messages."""
            websocket_url = 'ws://{host}:{port}/display'.format(
                host=websocket_config['host'],
                port=8282
            )
            LOG.info('Connecting to display websocket on ' + websocket_url)
            self.display_bus_client = WebSocketApp(
                url=websocket_url,
                on_open=self.on_display_bus_open,
            )
            create_daemon(self.display_bus_client.run_forever)
            LOG.info('Display websocket client started successfully')
        except:
            LOG.error("interface.py:_connect_to_display_bus() - Can't Connect to display bus!")

    def on_display_bus_open(self):
        """Let the display know that the display bus is ready."""
        LOG.info('Display message bus ready for connections')
        self.bus.emit(Message('display.bus.ready'))

    def on_core_ready(self, _):
        """When core reports that it is ready for use, update display."""
        if not self.is_pairing:
            self._finish_screen('loading', wait_for_it=5)
            self._show_screen('splash')
            self.finished_loading = True
            Timer(7, self.show_idle).start()

    def show_idle(self):
        """Force the idle screen when the Mark II skill does not."""
        self.active_screen = None
        message = Message(msg_type='mycroft.device.show.idle')
        self.bus.emit(message)

    def on_display_screen_show(self, message):
        """Send a message to the display bus that will show a screen."""
        if message.data['active_until_stopped']:
            self.active_until_stopped = message.data['screen_name']
        self._show_screen(
            message.data['screen_name'],
            message.data.get('screen_data')
        )

    def _show_screen(self, screen_name, screen_data=None):
        """Issue an event to the bus that will result in a screen update."""
        LOG.info('Received request to show "{}" screen '.format(screen_name))
        ignore = self._ignore_screen_show_request(screen_name)
        if not ignore:
            if self.active_screen == self.active_until_stopped:
                pause_active = (
                        self.active_screen is not None
                        and screen_name != self.active_screen
                )
                if pause_active:
                    LOG.info('Pausing "{}" screen'.format(self.active_screen))
                    self.paused_screen = self.active_screen
            LOG.info('Activating "{}" screen'.format(screen_name))
            self.active_screen = screen_name
            message_data = dict(screen_name=screen_name)
            if screen_data is not None:
                message_data.update(screen_data=screen_data)
            self._send_message_to_display_bus(
                message_type='display.screen.show',
                message_data=message_data
            )

    def _ignore_screen_show_request(self, screen_name):
        """Some requests to show a screen should be ignored.

        For example, do not show the idle screen when another screen is
        actively using the display.
        """
        ignore_reasons = []
        if screen_name == 'idle':
            if self.active_screen is not None and self.active_screen != 'idle':
                reason = 'The "{}" screen is active, ignore idle'.format(
                    self.active_screen
                )
                ignore_reasons.append(reason)
        if screen_name == self.paused_screen:
            ignore_reasons.append('Screen "{}" is paused'.format(screen_name))

        if ignore_reasons:
            log_msg = 'Ignoring request to show "{}" screen.  Reasons: {}'
            LOG.info(log_msg.format(screen_name, '\n\t'.join(ignore_reasons)))

        return len(ignore_reasons) > 0

    def reset_display(self, _):
        """When a skill is finished doing its thing, reset for next skill."""
        if self.finished_loading:
            if self.paused_screen is None:
                if self.active_screen != self.active_until_stopped:
                    LOG.info('Resetting active screen.')
                    self.active_screen = None
            else:
                log_msg = 'Resuming paused "{}" screen'
                LOG.info(log_msg.format(self.active_until_stopped))
                self.active_screen = self.paused_screen
                self.paused_screen = None

    def on_display_screen_update(self, message):
        """Send a message to the display bus updating a screen's data."""
        self._send_message_to_display_bus(
            message_type='display.screen.update',
            message_data=message.data
        )

    def _send_message_to_display_bus(self, message_type, message_data):
        """Helper method for sending messages to the display bus."""
        msg = dict(type=message_type, data=message_data)
        msg = json.dumps(msg)
        if self.display_bus_client is None:
            websocket_config = self.global_config.get("gui_websocket")
            start_display_message_bus(websocket_config)
            self._connect_to_display_bus(websocket_config)

        self.display_bus_client.send(msg)

    def on_display_screen_stop(self, message):
        """Handle stopping a skill that has control of the screen."""
        stop_source = message.data.get('source')
        if stop_source is None:
            self.active_screen = None
            self.active_until_stopped = None
            sleep(5)
            self.show_idle()

    def show_generic_screen(self, message):
        """Display viseme for skills that do not otherwise use the display."""
        if self.active_screen in (None, 'thinking'):
            LOG.info('no displayed skill found, sending generic screen')
            self._show_screen(screen_name='generic', screen_data=message.data)
            self.active_screen = 'generic'
            # Show idle screen after the visemes are done (+ 2 sec).
            time = message.data['visemes'][-1][1] + 2
            Timer(time, self.show_idle).start()

    def show_thinking_screen(self, _):
        """Show the thinking screen while the device searches for answers."""
        self._show_screen(screen_name='thinking')
        self.active_screen = 'thinking'

    def handle_play_start(self, _):
        self.active_until_stopped = self.active_screen = 'play'
        self._show_screen(screen_name='play')

    def show_play_screen(self, message):
        """Show the screen used for various audio play skills."""
        self._show_screen(screen_name='play', screen_data=message.data)

    def on_internet_connected(self, _):
        """Once connected to the internet, change the screen displayed."""
        self._finish_screen(screen_name='loading', wait_for_it=5)
        self._show_screen('wifi_connected')
        sleep(2)
        screen_data = dict(loading_status='LOADING SKILLS')
        self._show_screen('loading', screen_data)

    def start_pairing(self, _):
        self.is_pairing = True
        self._finish_screen('loading', wait_for_it=3)
        self._show_screen('pairing_start')

    def handle_paired(self, _):
        """When pairing succeeds, show success screen, then example intents."""
        self._show_screen('pairing_success')
        sleep(4)
        self._show_screen('example_intent')
        sleep(15)
        self.is_pairing = False
        self.show_idle()

    def handle_access_point_up(self, _):
        """When access point is up, display access point instructions"""
        self._show_screen('access_point')

    def handle_access_point_connected(self, _):
        """When connected to access point, display wifi instructions"""
        self._show_screen('wifi_start')
        sleep(8)
        self._show_screen('wifi_login')

    def _finish_screen(self, screen_name, wait_for_it=None):
        """Some screens have to finish what they are doing before exiting."""
        self._send_message_to_display_bus(
            message_type='display.screen.finish',
            message_data=dict(screen_name=screen_name)
        )
        if wait_for_it is not None:
            sleep(wait_for_it)

    def terminate(self):
        LOG.debug("Mark2 - calling m2enc terminate")
        self.m2enc.terminate()
        LOG.debug("Mark2 - m2enc terminated")

