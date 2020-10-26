import os
from mycroft.enclosure.MycroftHardware.MycroftLed import MycroftLed

class Led(MycroftLed):
    """note: we try to minimize the number of led writes 
       by not writing the same value to the same led"""

    real_num_leds = 12      # physical
    num_leds = 10           # logical
    device_addr = 74
    num_bytes  = 4
    fifty_zeros = "0 " * 50
    black = (0,0,0)
    vfctrl = "/home/pi/sj201_revB/vfctrl_usb"

    def __init__(self):
        self.shadow_leds = list((self.black,) * self.num_leds)
        self.buffered_leds = list((self.black,) * self.num_leds)
        self.capabilities = {
                        "num_leds":10,
                        "led_colors":"MycroftPalette",
                        "reserved_leds":[10,11],
                    }


    def get_capabilities(self):
        return self.capabilities


    def _set_led(self,pixel,colors):
        """physically set the led and update its shadow"""
        if pixel < self.num_leds:
            self.shadow_leds[pixel] = colors

        cmd = "sudo %s SET_I2C_WITH_REG " % (self.vfctrl,)
        cmd += "%d %d %d %d %d %d %s" % (
                self.device_addr,
                pixel,
                self.num_bytes,
                colors[0],
                colors[1],
                colors[2],
                self.fifty_zeros
                )
        os.system(cmd)

    def _show(self, new_leds):
        """show all given leds. new_leds is an array of led tuples"""
        it_old = iter(self.shadow_leds)
        r = iter(range(self.num_leds))
        # only update leds that actually changed
        [self._set_led(next(r),x) if next(it_old) != x else next(r) for x in new_leds]

    def show(self):
        """show buffered leds"""
        self._show(self.buffered_leds)

    def set_led(self, pixel, color_tuple, immediate):
        """set led, maybe immediately"""
        self.buffered_leds[pixel] = color_tuple
        if immediate and self.buffered_leds[pixel] != self.shadow_leds[pixel]:
            self._set_led(pixel, color_tuple)

    def fill(self, color):
        """fill all leds with the same color"""
        self.buffered_leds = list((color,) * self.num_leds)
        self.show()

    def set_leds(self, new_leds):
        """set leds from tuple array"""
        self.buffered_leds = new_leds
        self.show()

