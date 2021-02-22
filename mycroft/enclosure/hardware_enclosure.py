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

import importlib
import threading
import time
from mycroft.util import create_signal
import RPi.GPIO as GPIO
import os
from mycroft.util.log import LOG


class HardwareEnclosure:
    mute_led = 11    # last led is reserved for mute mic switch

    def __init__(self, enclosure_type, board_type=None):
        LOG.info("Mark2 Starting HardwareEnclosure()")
        self.enclosure_type = enclosure_type
        self.board_type = board_type

        self.max_volume = 1.0
        self.min_volume = 0.0
        self.shadow_volume = 0.5
        self.volume_increment = 0.1
        self.last_action = time.time()
        self.last_mute = -1

        driver_dir = "mycroft.enclosure.hardware"

        capabilities_module = driver_dir + ".%s" % (self.enclosure_type,)
        module = importlib.import_module(capabilities_module)
        enclosure_capabilities = module.Capabilities()
        if self.board_type is None:
            self.board_type = enclosure_capabilities.board_type
        self.capabilities = enclosure_capabilities.capabilities[self.board_type]

        # eventually this could also be driven by the capabilities
        # in fact it is actually a BUG that it is not, as every 
        # enclosure does not need the exact same hardware configuration.
        led_driver = self.capabilities["Led"]["name"]
        switch_driver = self.capabilities["Switch"]["name"]
        volume_driver = self.capabilities["Volume"]["name"]
        fan_driver = self.capabilities["Fan"]["name"]

        pal_module = driver_dir + ".MycroftLed.%s" % (self.capabilities["Palette"]["name"],)
        module = importlib.import_module(pal_module)
        self.palette = module.Palette()

        led_module = driver_dir + ".MycroftLed.%s" % (led_driver,)
        module = importlib.import_module(led_module)
        self.leds = module.Led()

        vol_module = driver_dir + ".MycroftVolume.%s" % (volume_driver,)
        module = importlib.import_module(vol_module)
        self.hardware_volume = module.Volume()

        fan_module = driver_dir + ".MycroftFan.%s" % (fan_driver,)
        module = importlib.import_module(fan_module)
        self.fan = module.FanControl()

        switch_module = driver_dir + ".MycroftSwitch.%s" % (switch_driver,)
        module = importlib.import_module(switch_module)
        self.switches = module.Switch()

        self.switches.user_action_handler = self.handle_action
        self.overide_action = None
        self.switches.user_mute_handler = self.handle_mute
        self.switches.user_volup_handler = self.handle_vol_up
        self.switches.user_voldown_handler = self.handle_vol_down

        # volume display timeout
        self.watchdog = None
        self.watchdog_timeout = 5

        LOG.info("Mark2 HardwareEnclosure() initialized")

    def get_capabilities(self):
        return self.capabilities

    def handle_watchdog(self):
        # clear the volume leds
        self.leds.fill( self.palette.BLACK )
        self.watchdog = None

    def cancel_watchdog(self):
        if self.watchdog is not None:
            self.watchdog.cancel()

    def show_volume(self, vol):
        new_leds = []
        vol = int(vol * 10)

        for x in range(vol):
            new_leds.append( self.palette.BLUE )

        for x in range(self.leds.num_leds - vol):
            new_leds.append( self.palette.BLACK )

        self.leds.set_leds( new_leds )
        self.cancel_watchdog()
        self.watchdog = threading.Timer(self.watchdog_timeout,
                                        self.handle_watchdog)
        self.watchdog.start()

    def handle_action(self):
        LOG.debug("Mark2:HardwareEnclosure:handle_action()")
        # debounce this 10 seconds
        if time.time() - self.last_action > 10:
            self.last_action = time.time()
            if self.overide_action is not None:
                self.overide_action()
            else:
                create_signal('buttonPress')

    def handle_mute(self, val):
        LOG.debug("Mark2:HardwareEnclosure:handle_mute() - val = %s" % (val,))
        if val != self.last_mute:
            self.last_mute = val
            if val == 0:
                self.leds._set_led_with_brightness(
                        self.mute_led, 
                        self.palette.GREEN, 
                        0.5)
            else:
                self.leds._set_led_with_brightness(
                        self.mute_led, 
                        self.palette.RED, 
                        0.5)

    def handle_vol_down(self):
        self.shadow_volume = self.hardware_volume.get_volume()
        LOG.debug("Mark2:HardwareEnclosure:handle_vol_down()-was %s" % (self.shadow_volume))
        if self.shadow_volume > self.min_volume:
            self.shadow_volume -= self.volume_increment

        self.hardware_volume.set_volume(self.shadow_volume)
        self.show_volume(self.shadow_volume)

    def handle_vol_up(self):
        self.shadow_volume = self.hardware_volume.get_volume()
        LOG.debug("Mark2:HardwareEnclosure:handle_vol_up()-was %s" % (self.shadow_volume))
        if self.shadow_volume < self.max_volume:
            self.shadow_volume += self.volume_increment

        self.hardware_volume.set_volume(self.shadow_volume)
        self.show_volume(self.shadow_volume)

    def terminate(self):
        LOG.info("Mark2:HardwareEnclosure:terminate()")
        self.cancel_watchdog()
        self.leds.fill( self.palette.BLACK )
        self.switches.terminate()
        self.switches._running = False

        if self.switches.thread_handle is not None:
            self.switches.thread_handle.join()
