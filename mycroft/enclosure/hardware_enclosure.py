import importlib
import threading
import time
from mycroft.util import create_signal

class HardwareEnclosure:
    mute_led = 11    # last led is reserved for mute mic switch

    def __init__(self, enclosure_type):
        self.enclosure_type = enclosure_type

        self.capabilities = {
                     "Led":{"name":"leds", "type":"MycroftLed"}, 
                     "Switch":{"name":"switches", "type":"MycroftSwitch"}, 
                     "Volume":{"name":"hardware_volume", "type":"MycroftVolume"}, 
                     "Palette":{"name":"palette", "type":"MycroftPalette"}
                     }

        self.max_volume = 10
        self.shadow_volume = 5
        self.volume_increment = 1
        self.last_action = time.time()
        self.last_mute = 0

        driver_dir = "mycroft.enclosure.%s" % (enclosure_type,)

        # could loop through capabilities ...
        pal_module = driver_dir + ".palette"
        module = importlib.import_module(pal_module)
        self.palette = module.Palette()

        led_module = driver_dir + ".led"
        module = importlib.import_module(led_module)
        self.leds = module.Led()

        vol_module = driver_dir + ".volume"
        module = importlib.import_module(vol_module)
        self.hardware_volume = module.Volume()

        switch_module = driver_dir + ".switch"
        module = importlib.import_module(switch_module)
        self.switches = module.Switch()

        self.switches.user_action_handler = self.handle_action
        self.switches.user_mute_handler = self.handle_mute
        self.switches.user_volup_handler = self.handle_vol_up
        self.switches.user_voldown_handler = self.handle_vol_down

        # TODO - pull up/down verified!!!
        self.leds._set_led(self.mute_led, self.palette.GREEN)

        # volume display timeout
        self.watchdog = None
        self.watchdog_timeout = 5


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
        self.leds.fill( self.palette.BLACK )
        self.cancel_watchdog()
        self.switches.terminate()

        # Wait for actual termination
        self.switches.thread_handle.join()

        self.leds._set_led(self.mute_led,self.palette.BLACK)

