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

from mycroft.enclosure.hardware.MockSMBus import MockSMBus
from mycroft.enclosure.hardware.MycroftLed.MycroftLed import MycroftLed
from mycroft.util.log import LOG


class Led(MycroftLed):
    """A dummy LED control class used for testing.

    This class has been kept as close as possible to the SJ201 version for
    testing purposes.
    """

    real_num_leds = 12  # physical
    num_leds = 10  # logical
    black = (0, 0, 0)  # TODO pull from pallette
    device_addr = 0x04

    def __init__(self):
        self.bus = MockSMBus()
        self.brightness = 0.5
        self.capabilities = {
            "num_leds": self.num_leds,
            "brightness": "(0.0-1.0)",
            "led_colors": "MycroftPalette",
            "reserved_leds": list(range(self.num_leds, self.real_num_leds)),
        }

    def adjust_brightness(self, cval, bval):
        return min(255, cval * bval)

    def get_capabilities(self):
        return self.capabilities

    def _set_led(self, pixel, color):
        """internal interface
        permits access to the
        reserved leds"""
        red_val = int(color[0])
        green_val = int(color[1])
        blue_val = int(color[2])

        self.bus.write_i2c_block_data(
            self.device_addr, pixel, [red_val, green_val, blue_val]
        )

    def _set_led_with_brightness(self, pixel, color, blevel):
        self._set_led(pixel, list(map(self.adjust_brightness, color, (blevel,) * 3)))

    def show(self):
        """show buffered leds, only used
        for older slower devices"""
        pass

    def set_led(self, pixel, color):
        """external interface enforces led
        reservation and honors brightness"""
        self._set_led(
            pixel % self.num_leds,
            list(map(self.adjust_brightness, color, (self.brightness,) * 3)),
        )

    def fill(self, color):
        """fill all leds with the same color"""
        rgb = [int(self.adjust_brightness(c, self.brightness)) for c in color[:3]]

        # Write all colors at once
        self.bus.write_i2c_block_data(self.device_addr, 0, rgb * self.num_leds)

    def set_leds(self, new_leds):
        """set leds from tuple array"""
        for x in range(0, self.num_leds):
            self.set_led(x, new_leds[x])
