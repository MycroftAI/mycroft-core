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

        self.max_volume = 10
        self.shadow_volume = 5
        self.volume_increment = 1
        self.last_action = time.time()
        self.last_mute = 0

        driver_dir = "mycroft.enclosure.hardware"

        capabilities_module = driver_dir + ".%s" % (self.enclosure_type,)
        module = importlib.import_module(capabilities_module)
        enclosure_capabilities = module.Capabilities()
        if self.board_type is None:
            self.board_type = enclosure_capabilities.board_type
        self.capabilities = enclosure_capabilities.capabilities[self.board_type]

        # eventually this could also be driven by the capabilities
        led_driver = self.capabilities["Led"]["name"]
        switch_driver = self.capabilities["Switch"]["name"]
        volume_driver = self.capabilities["Volume"]["name"]

        pal_module = driver_dir + ".MycroftLed.%s" % (self.capabilities["Palette"]["name"],)
        module = importlib.import_module(pal_module)
        self.palette = module.Palette()

        led_module = driver_dir + ".MycroftLed.%s" % (led_driver,)
        module = importlib.import_module(led_module)
        self.leds = module.Led()

        vol_module = driver_dir + ".MycroftVolume.%s" % (volume_driver,)
        module = importlib.import_module(vol_module)
        self.hardware_volume = module.Volume()

        switch_module = driver_dir + ".MycroftSwitch.%s" % (switch_driver,)
        module = importlib.import_module(switch_module)
        self.switches = module.Switch()

        self.switches.user_action_handler = self.handle_action
        self.overide_action = self.reset_xmos
        self.switches.user_mute_handler = self.handle_mute
        self.switches.user_volup_handler = self.handle_vol_up
        self.switches.user_voldown_handler = self.handle_vol_down

        # TODO - pull up/down verified!!!
        self.leds._set_led(self.mute_led, self.palette.GREEN)

        # volume display timeout
        self.watchdog = None
        self.watchdog_timeout = 5

        LOG.info("Mark2 HardwareEnclosure() initialized")


    # BUG FIX temp fix for faulty hardware
    def reset_xmos(self):
        LOG.error("Mark2 Start Reset Hardware ...")
        LOG.error("Mark2 Stopping services ...")
        os.system("~/mycroft-core/stop-mycroft.sh voice")
        os.system("~/mycroft-core/stop-mycroft.sh audio")
        LOG.error("Mark2 LEDs Red ...")
        self.leds.fill( self.palette.RED )
        time.sleep(5)
        LOG.error("Mark2 Reset Hardware ...")
        self.switches.reset_hardware()
        LOG.error("Mark2 Sleep after Hardware Reset ...")
        time.sleep(15)
        LOG.error("Mark2 Start audio svc ...")
        os.system("~/mycroft-core/start-mycroft.sh audio")
        time.sleep(10)
        LOG.error("Mark2 Start voice svc ...")
        os.system("~/mycroft-core/start-mycroft.sh voice")
        time.sleep(3)
        self.leds.fill( self.palette.BLACK )
        os.system("aplay ~/mycroft-core/mycroft/res/snd/start_listening.wav")
        LOG.error("Mark2 Completed Reset Hardware ...")


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
        # debounce this 10 seconds
        if time.time() - self.last_action > 10:
            self.last_action = time.time()
            if self.overide_action is not None:
                self.overide_action()
            else:
                create_signal('buttonPress')

    def handle_mute(self, val):
        if val != self.last_mute:
            self.last_mute = val
            if val == 0:
                self.leds._set_led(self.mute_led, self.palette.GREEN)
            else:
                self.leds._set_led(self.mute_led, self.palette.RED)

    def handle_vol_down(self):
        if self.shadow_volume > 0:
            self.shadow_volume -= self.volume_increment

        self.hardware_volume.set_volume(self.shadow_volume)
        self.show_volume(self.shadow_volume)

    def handle_vol_up(self):
        if self.shadow_volume < self.max_volume:
            self.shadow_volume += self.volume_increment

        self.hardware_volume.set_volume(self.shadow_volume)
        self.show_volume(self.shadow_volume)

    def terminate(self):
        self.cancel_watchdog()
        self.leds.fill( self.palette.BLACK )
        self.switches._running = False
        self.switches.terminate()

        if self.switches.thread_handle is not None:
            self.switches.thread_handle.join()
