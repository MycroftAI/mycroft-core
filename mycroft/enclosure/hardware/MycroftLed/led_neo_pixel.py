# Copyright 2020 Mycroft AI Inc.
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

from subprocess import Popen


class Led:
    """
    Class to manipulate the LEDs on an SJ201
    Conforms to the same interface for all Mycroft
    LED devices
    """

    def __init__(self):
        self.num_leds = 12  # sj201 has 12
        self.leds = list(((0, 0, 0),) * self.num_leds)
        self.capabilities = {
            "num_leds": 10,
            "led_colors": "MycroftPalette",
            "reserved_leds": [10, 11],
        }

    def get_capabilities(self):
        return self.capabilities

    def _update_leds(self):
        cmd = "sudo "
        cmd += "/opt/mycroft/mycroft/enclosure/hardware/util/"
        cmd += "neo_pixel_set_leds.py "

        cmd += " ".join(map(str, [item for sublist in self.leds for item in sublist]))

        process = Popen(cmd, shell=True)

    def fill(self, color):
        """set all leds to the same color"""
        self.leds = list((color,) * self.num_leds)
        self._update_leds()

    def set_leds(self, input_leds):
        """set all leds from list of tuples"""
        for x in range(self.num_leds):
            self.leds[x] = input_leds[x]
        self._update_leds()

    def get_leds(self):
        """get a list of color rgb tuples"""
        return self.leds

    def set_led(self, which, color):
        """set a led to some color where color is an RGB tuple"""
        self.leds[which % self.num_leds] = color
        self._update_leds()

    def get_led(self, which):
        """get the color (rgb tuple) of a particular led."""
        return self.leds[which % self.num_leds]

    def _set_led(self, which, color):
        return self.set_led(which, color)
