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
import threading
 
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
    _SW_ACTION = 22
    _SW_VOL_UP = 23
    _SW_VOL_DOWN = 24 
    _SW_MUTE = 25

    RED = (255,0,0)
    GREEN = (0,255,0)
    BLUE = (0,0,255)
    BLACK = (0,0,0)
    WHITE = (255,255,255)

    def __init__(self, debounce=100):
        self.debounce = debounce
        self.leds = None
        self.volume = None
        self.watchdog = None
        self.watchdog_timeout = 5
        self.active = 0
        self.vol_increment = 0.1
        self.thread_handle = None

        # use BCM GPIO numbering
        GPIO.setmode(GPIO.BCM)

        # we need to pull up the 3 buttons
        GPIO.setup(self._SW_ACTION, 
            GPIO.IN, 
            pull_up_down=GPIO.PUD_UP)

        GPIO.setup(self._SW_VOL_UP, 
            GPIO.IN, 
            pull_up_down=GPIO.PUD_UP)

        GPIO.setup(self._SW_VOL_DOWN, 
            GPIO.IN, 
            pull_up_down=GPIO.PUD_UP)

        GPIO.setup(self._SW_MUTE, GPIO.IN)

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
        GPIO.add_event_detect(self._SW_ACTION, 
            GPIO.BOTH, 
            callback=self.action_handler, 
            bouncetime=debounce)

        GPIO.add_event_detect(self._SW_VOL_UP, 
            GPIO.BOTH, 
            callback=self.vol_up_handler, 
            bouncetime=debounce)

        GPIO.add_event_detect(self._SW_VOL_DOWN, 
            GPIO.BOTH, 
            callback=self.vol_down_handler, 
            bouncetime=debounce)

        GPIO.add_event_detect(self._SW_MUTE, 
            GPIO.BOTH, 
            callback=self.mute_handler, 
            bouncetime=debounce)

        # user must set these
        self.user_voldown_handler = None
        self.user_volup_handler = None
        self.user_action_handler = None
        self.user_mute_handler = None

        self.capabilities = {
                    "user_volup_handler":"button",
                    "user_voldown_handler":"button",
                    "user_action_handler":"button",
                    "user_mute_handler":"slider"
                }

    def get_capabilities(self):
        return self.capabilities

    def handle_watchdog(self):
        # after brief delay clear the volume leds
        self.leds.fill_leds( self.BLACK )
        self.watchdog = None
        
    def handle_action(self, channel):
        self.SW_ACTION = GPIO.input(self._SW_ACTION)
        if self.user_action_handler is not None and self.SW_ACTION == self.active:
            self.user_action_handler()

    def handle_vol_up(self, channel):
        self.SW_VOL_UP = GPIO.input(self._SW_VOL_UP)
        if self.user_volup_handler is not None and self.SW_VOL_UP == self.active:
            self.user_volup_handler()

        """
        if self.leds is not None and self.SW_VOL_UP == self.active:
            vol = self.volume.get_hardware_volume()
            vol += self.vol_increment
            self.volume.set_hardware_volume(vol)
            vol = int(vol * 10)  # note we are only using 10 of the 12 leds 
            new_leds = []

            for x in range(vol):
                new_leds.append( self.GREEN )

            for x in range(self.leds.num_leds - vol):
                new_leds.append( self.BLACK )

            self.leds.set_leds( new_leds )

            if self.watchdog is not None:
                self.watchdog.cancel()

            self.watchdog = threading.Timer(
                                            self.watchdog_timeout, 
                                            self.handle_watchdog
                                           )
            self.watchdog.start()
        """

    def handle_vol_down(self, channel):
        self.SW_VOL_DOWN = GPIO.input(self._SW_VOL_DOWN)
        if self.user_voldown_handler is not None and self.SW_VOL_DOWN == self.active:
            self.user_voldown_handler()

        """
        if self.leds is not None and self.SW_VOL_DOWN == self.active:
            vol = self.volume.get_hardware_volume()
            vol -= self.vol_increment
            self.volume.set_hardware_volume(vol)
            vol = int(vol * 10)
            new_leds = []

            for x in range(vol):
                new_leds.append( self.RED )

            for x in range(self.leds.num_leds - vol):
                new_leds.append( self.BLACK )

            self.leds.set_leds( new_leds )

            if self.watchdog is not None:
                self.watchdog.cancel()

            self.watchdog = threading.Timer(5, self.handle_watchdog)
            self.watchdog.start()
        """

    def handle_mute(self, channel):
        self.SW_MUTE = GPIO.input(self._SW_MUTE)
        print("Inside handle hardware mute = %s" % (self.SW_MUTE))
        if self.user_mute_handler is not None:
            self.user_mute_handler()

    def terminate(self):
        pass
