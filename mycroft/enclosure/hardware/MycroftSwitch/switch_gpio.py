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

import RPi.GPIO as GPIO
import time
from mycroft.util.log import LOG


class Switch:
    """
    Class to handle the Mark2 switches.
    Note - a switch is an abstract concept
    which applies to buttons and switches.
    The Mark2 actually has 4 different switches.
    Three buttons (volume up, down and activate)
    and a mute mic switch. All are read only
    and interrupt driven. Also note switches are
    pulled up so the active state is actually zero.
    """

    # GPIO pin numbers
    """ old sj201 mappings
    _SW_ACTION = 22
    _SW_VOL_UP = 23
    _SW_VOL_DOWN = 24
    _SW_MUTE = 25
    """
    # sj201Rev4
    _SW_VOL_UP = 22
    _SW_VOL_DOWN = 23
    _SW_ACTION = 24
    _SW_MUTE = 25

    _XMOS_POWER = 16  # Enable1V
    _XMOS_RESET = 27  # Reset XMOS

    def __init__(self, debounce=100):
        self.debounce = debounce
        self.active = 0

        # some switch implementations require a thread
        # we don't but we must meet the base requirement
        self.thread_handle = None

        self.capabilities = {
            "user_volup_handler": "button",
            "user_voldown_handler": "button",
            "user_action_handler": "button",
            "user_mute_handler": "slider",
        }

        # use BCM GPIO pin numbering
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        """
        # xmos related
        GPIO.setup(self._XMOS_POWER, GPIO.OUT)
        GPIO.setup(self._XMOS_RESET, GPIO.OUT)

        # power up the xmos
        #self.reset_xmos()
        time.sleep(0.001)
        GPIO.output(self._XMOS_POWER, 1)
        time.sleep(0.001)
        GPIO.output(self._XMOS_RESET, 1)
        """

        # we need to pull up the 3 buttons
        GPIO.setup(self._SW_ACTION, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self._SW_VOL_UP, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self._SW_VOL_DOWN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self._SW_MUTE, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # establish default values
        self.SW_ACTION = GPIO.input(self._SW_ACTION)
        self.SW_VOL_UP = GPIO.input(self._SW_VOL_UP)
        self.SW_VOL_DOWN = GPIO.input(self._SW_VOL_DOWN)
        self.SW_MUTE = GPIO.input(self._SW_MUTE)

        # establish default handlers for each switch
        self.action_handler = self.handle_action
        self.vol_up_handler = self.handle_vol_up
        self.vol_down_handler = self.handle_vol_down
        self.mute_handler = self.handle_mute

        # attach callbacks
        GPIO.add_event_detect(
            self._SW_ACTION,
            GPIO.BOTH,
            callback=self.action_handler,
            bouncetime=debounce,
        )

        GPIO.add_event_detect(
            self._SW_VOL_UP,
            GPIO.BOTH,
            callback=self.vol_up_handler,
            bouncetime=debounce,
        )

        GPIO.add_event_detect(
            self._SW_VOL_DOWN,
            GPIO.BOTH,
            callback=self.vol_down_handler,
            bouncetime=debounce,
        )

        GPIO.add_event_detect(
            self._SW_MUTE, GPIO.BOTH, callback=self.mute_handler, bouncetime=debounce
        )

        # user overides
        self.user_voldown_handler = None
        self.user_volup_handler = None
        self.user_action_handler = None
        self.user_mute_handler = None

    def get_capabilities(self):
        return self.capabilities

    def handle_action(self, channel):
        self.SW_ACTION = GPIO.input(self._SW_ACTION)
        if self.SW_ACTION == self.active:
            if self.user_action_handler is not None:
                self.user_action_handler()

    def handle_vol_up(self, channel):
        self.SW_VOL_UP = GPIO.input(self._SW_VOL_UP)
        if self.SW_VOL_UP == self.active:
            if self.user_volup_handler is not None:
                self.user_volup_handler()

    def handle_vol_down(self, channel):
        self.SW_VOL_DOWN = GPIO.input(self._SW_VOL_DOWN)
        if self.SW_VOL_DOWN == self.active:
            if self.user_voldown_handler is not None:
                self.user_voldown_handler()

    def handle_mute(self, channel):
        # No idea why this delay is necessary, but it makes the muting reliable
        time.sleep(0.05)
        self.SW_MUTE = GPIO.input(self._SW_MUTE)

        if self.user_mute_handler is not None:
            self.user_mute_handler(self.SW_MUTE)

    # recycle xmos power
    def reset_xmos(self):
        LOG.info("switch_gpio: reset_xmos() hit")
        """
        GPIO.output(self._XMOS_RESET, 0)
        time.sleep(0.001)
        GPIO.output(self._XMOS_POWER, 0)
        time.sleep(0.001)
        GPIO.output(self._XMOS_POWER, 1)
        time.sleep(0.001)
        GPIO.output(self._XMOS_RESET, 1)
        """

    def terminate(self):
        LOG.info("switch_gpio: terminate hit, calling GPIO.cleanup()")
        # GPIO.cleanup()
