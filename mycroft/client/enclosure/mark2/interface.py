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
import time
from threading import Timer
from websocket import WebSocketApp

from mycroft.client.enclosure.base import Enclosure
from mycroft.messagebus.message import Message
from mycroft.util import create_daemon, connected
from mycroft.util.log import LOG
from mycroft.enclosure.hardware_enclosure import HardwareEnclosure


class EnclosureMark2(Enclosure):
    def __init__(self):
        LOG.info('** Initialize EnclosureMark2 **')
        super().__init__()
        self.display_bus_client = None
        self._define_event_handlers()
        self.finished_loading = False
        self.active_screen = 'loading'
        self.paused_screen = None
        self.is_pairing = False
        self.active_until_stopped = None
        self.reserved_led = 10
        self.mute_led = 11

        self.system_volume = 0.5   # pulse audio master system volume
        # if you want to do anything with the system volume
        # (ala pulseaudio, etc) do it here!
        self.current_volume = 0.5 # hardware/board level volume

        # TODO these need to come from a config value
        self.m2enc = HardwareEnclosure("Mark2", "sj201r4")

        self.m2enc.leds._set_led_with_brightness(
                self.reserved_led, 
                self.m2enc.palette.YELLOW, 
                0.5)

        self.m2enc.leds._set_led_with_brightness(
                self.mute_led, 
                self.m2enc.palette.GREEN, 
                1.0)

        LOG.info('** EnclosureMark2 initalized **')
        self.bus.once('mycroft.skills.trained', self.is_device_ready)

    def is_device_ready(self, message):
        is_ready = False
        # Bus service assumed to be alive if messages sent and received
        # Enclosure assumed to be alive if this method is running
        services = {'audio': False, 'speech': False, 'skills': False}
        start = time.monotonic()
        while not is_ready:
            is_ready = self.check_services_ready(services)
            if is_ready:
                break
            elif time.monotonic() - start >= 60:
                raise Exception('Timeout waiting for services start.')
            else:
                time.sleep(3)

        if is_ready:
            LOG.info("All Mycroft Services have reported ready.")
            if connected():
                self.bus.emit(Message('mycroft.ready'))
            else:
                self.bus.emit(Message('mycroft.wifi.setup'))

        return is_ready

    def check_services_ready(self, services):
        """Report if all specified services are ready.

        services (iterable): service names to check.
        """
        for ser in services:
            services[ser] = False
            response = self.bus.wait_for_response(Message(
                                'mycroft.{}.is_ready'.format(ser)))
            if response and response.data['status']:
                services[ser] = True
        return all([services[ser] for ser in services])


    def _define_event_handlers(self):
        """Assign methods to act upon message bus events."""
        self.bus.on('mycroft.volume.set', self.on_volume_set)
        self.bus.on('mycroft.volume.get', self.on_volume_get)
        self.bus.on('mycroft.volume.duck', self.on_volume_duck)
        self.bus.on('mycroft.volume.unduck', self.on_volume_unduck)

    def on_volume_duck(self, message):
        LOG.warning("Mark2 volume duck deprecated! use volume set instead.")

    def on_volume_unduck(self, message):
        LOG.warning("Mark2 volume unduck deprecated! use volume set instead.")

    def on_volume_set(self, message):
        self.current_volume = message.data.get("percent",self.current_volume)
        LOG.info('Mark2:interface.py set volume to %s' % (self.current_volume,))
        self.m2enc.hardware_volume.set_volume(float(self.current_volume))

    def on_volume_get(self, message):
        LOG.info('Mark2:interface.py get and emit volume %s' % (self.current_volume,))
        self.bus.emit(
                message.response(
                    data={'percent': self.current_volume, 'muted': False}))

    def terminate(self):
        self.m2enc.leds._set_led(10,(0,0,0)) # blank out reserved led
        self.m2enc.leds._set_led(11,(0,0,0)) # BUG set to real value!
        self.m2enc.terminate()
