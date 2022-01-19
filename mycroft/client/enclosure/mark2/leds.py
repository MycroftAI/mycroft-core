# Copyright 2021 Mycroft AI Inc.
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
import time
import typing

from mycroft.util.log import LOG


class LedAnimation:
    """Base class for LED animations"""

    def __init__(self, led_obj):
        self.led_obj = led_obj

    def start(self):
        """Begin LED animation"""
        pass

    def step(self, context: typing.Dict[str, typing.Any]) -> bool:
        """Single step of the animation.

        Put time.sleep inside here.

        Arguments:
            context: dict with user-defined values

        Returns:
            True if animation should continue
        """
        return False

    def stop(self):
        """End LED animation"""
        pass


class PulseLedAnimation(LedAnimation):
    def __init__(self, led_obj, pal_obj):
        super().__init__(led_obj)

        self.pal_obj = pal_obj
        self.exit_flag = False
        self.color_tup = self.pal_obj.MYCROFT_GREEN
        self.delay = 0.1
        self.brightness = 100
        self.step_size = 5
        self.tmp_leds = []

    def start(self):
        self.led_obj.fill(self.color_tup)

        self.brightness = 100
        self.led_obj.brightness = self.brightness / 100
        self.led_obj.fill(self.color_tup)

    def step(self, context):
        if (self.brightness + self.step_size) > 100:
            self.brightness = self.brightness - self.step_size
            self.step_size = self.step_size * -1

        elif (self.brightness + self.step_size) < 0:
            self.brightness = self.brightness - self.step_size
            self.step_size = self.step_size * -1

        else:
            self.brightness += self.step_size

        self.led_obj.brightness = self.brightness / 100
        self.led_obj.fill(self.color_tup)

        time.sleep(self.delay)
        return True

    def stop(self):
        self.led_obj.brightness = 1.0
        self.led_obj.fill(self.pal_obj.BLACK)


class ChaseLedAnimation(LedAnimation):
    def __init__(self, led_obj, background_color, foreground_color):
        super().__init__(led_obj)

        self.bkgnd_col = background_color
        self.fgnd_col = foreground_color
        self.exit_flag = False
        self.color_tup = foreground_color
        self.delay = 0.1

    def start(self):
        self.led_obj.fill(self.fgnd_col)

    def step(self, context):
        fgnd_col = context.get("chase.foreground_color", self.fgnd_col)
        bkgnd_col = context.get("chase.background_color", self.bkgnd_col)
        stop = context.get("chase.stop", False)

        for x in range(0, 10):
            self.led_obj.set_led(x, fgnd_col)
            time.sleep(self.delay)
            self.led_obj.set_led(x, bkgnd_col)

        if stop:
            return False

        return True

    def stop(self):
        self.led_obj.fill(self.led_obj.black)
