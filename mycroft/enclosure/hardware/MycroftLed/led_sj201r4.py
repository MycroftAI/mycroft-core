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
import os
from mycroft.enclosure.hardware.MycroftLed.MycroftLed import MycroftLed
from mycroft.util.log import LOG

class Led(MycroftLed):
    real_num_leds = 12      # physical
    num_leds = 10           # logical
    black = (0,0,0) # TODO pull from pallette
    device_addr = 0x04

    def __init__(self):
        self.brightness = 0.5
        self.capabilities = {
                        "num_leds":10,
                        "brightness":"(0.0-1.0)",
                        "led_colors":"MycroftPalette",
                        "reserved_leds":[10,11],
                    }

    def adjust_brightness(self, cval, bval):
        return min(255, cval * bval)

    def get_capabilities(self):
        return self.capabilities

    def _set_led(self, pixel, color):
        """ internal interface
            permits access to the 
            reserved leds """
        red_val   = color[0]
        green_val = color[1]
        blue_val  = color[2]

        cmd =   "i2cset -y 1 %d %d %d %d %d i " % (
                    self.device_addr,
                    pixel,
                    red_val,
                    green_val,
                    blue_val)
        os.system(cmd)
        LOG.debug("Execute %s" % (cmd,))

    def _set_led_with_brightness(self, pixel, color, blevel):
        self._set_led(
                pixel, 
                list(
                    map(
                        self.adjust_brightness, 
                        color, 
                        (blevel,) * 3)))

    def show(self):
        """ show buffered leds, only used
           for older slower devices """
        pass

    def set_led(self, pixel, color):
        """ external interface enforces led 
            reservation and honors brightness """
        self._set_led(
                pixel % self.num_leds, 
                list(
                    map(
                        self.adjust_brightness, 
                        color, 
                        (self.brightness,) * 3)))

    def fill(self, color):
        """fill all leds with the same color"""
        for x in range(0,10):
            self._set_led(x, color)

    def set_leds(self, new_leds):
        """set leds from tuple array"""
        for x in range(0,10):
            self.set_led(x, new_leds[x])

