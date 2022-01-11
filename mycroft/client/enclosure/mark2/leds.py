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

from mycroft.util.log import LOG

class LedAnimation:
    """Base class for LED animations"""
    def __init__(self, led_obj):
        self.led_obj = led_obj

    def run(self):
        pass

    def stop(self):
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

    def run(self):
        LOG.debug("pulse animation started")
        self.led_obj.fill(self.color_tup)

        self.brightness = 100
        self.led_obj.brightness = self.brightness / 100
        self.led_obj.fill(self.color_tup)

        self.exit_flag = False
        while not self.exit_flag:

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

        LOG.debug("pulse animation stopped")
        self.led_obj.brightness = 1.0
        self.led_obj.fill(self.pal_obj.BLACK)

    def stop(self):
        self.exit_flag = True


class ChaseLedAnimation(LedAnimation):
    def __init__(self, led_obj, background_color, foreground_color):
        super().__init__(led_obj)

        self.bkgnd_col = background_color
        self.fgnd_col = foreground_color
        self.exit_flag = False
        self.color_tup = foreground_color
        self.delay = 0.1

    def run(self):
        LOG.debug("chase animation started")
        chase_ctr = 0
        self.exit_flag = False

        self.led_obj.fill(self.bkgnd_col)
        while not self.exit_flag:
            chase_ctr += 1
            LOG.debug("chase animation %s", chase_ctr)
            for x in range(0, 10):
                self.led_obj.set_led(x, self.fgnd_col)
                time.sleep(self.delay)
                self.led_obj.set_led(x, self.bkgnd_col)
            if chase_ctr > 10:
                self.exit_flag = True

        LOG.debug("chase animation stopped")
        self.led_obj.fill(self.led_obj.black)

    def stop(self):
        self.exit_flag = True
