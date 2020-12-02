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
from mycroft.enclosure.hardware_enclosure import HardwareEnclosure


class EnclosureMark2(Enclosure):
    def __init__(self):
        LOG.info('** Starting Mark2 enclosure (interface.py) **')
        super().__init__()
        self.display_bus_client = None
        self._define_event_handlers()
        self.finished_loading = False
        self.active_screen = 'loading'
        self.paused_screen = None
        self.is_pairing = False
        self.active_until_stopped = None

        self.system_volume = 0.5   # pulse audio master system volume
        # if you want to do anything with the system volume
        # (ala pulseaudio, etc) do it here!
        self.hardware_volume = 0.5 # hardware/board level volume

        self.m2enc = HardwareEnclosure("Mark2", "xmos_volume_gpio_switches_xmos_leds")

        LOG.info('** Ending Mark2 enclosure init (interface.py) **')


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
        self.hardware_volume = message.data.get("percent", self.hardware_volume)
        self.m2enc.hardware_volume.set_hw_volume(self.hardware_volume)

    def on_volume_get(self, message):
        #self.bus.emit(message.response(data={'percent': self.hardware_volume, 'muted': False}))
        LOG.warning("Mark2 will not emit volume response!")


    def terminate(self):
        self.m2enc.terminate()

