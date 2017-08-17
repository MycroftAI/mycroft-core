# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

import mycroft.client.enclosure.display_manager as DisplayManager
from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger
from PIL import Image

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


'''
API for the functions that affect the Mark I device.
NOTE: current state management is poorly implemented,
will be changed in the future.
'''


class EnclosureAPI:
    """
    This API is intended to be used to interface with the hardware
    that is running Mycroft.  It exposes all possible commands which
    can be sent to a Mycroft enclosure implementation.

    Different enclosure implementations may implement this differently
    and/or may ignore certain API calls completely.  For example,
    the eyes_color() API might be ignore on a Mycroft that uses simple
    LEDs which only turn on/off, or not at all on an implementation
    where there is no face at all.
    """

    def __init__(self, ws, name=""):
        self.ws = ws
        self.name = name

    def register(self, skill_name=""):
        """Registers a skill as active. Used for speak() and speak_dialog()
        to 'patch' a previous implementation. Somewhat hacky.
        """
        if self.name != "":
            DisplayManager.set_active(self.name)
        else:
            DisplayManager.set_active(skill_name)

    def reset(self):
        """The enclosure should restore itself to a started state.
        Typically this would be represented by the eyes being 'open'
        and the mouth reset to its default (smile or blank).
        """
        self.ws.emit(Message("enclosure.reset"))

    def system_reset(self):
        """The enclosure hardware should reset any CPUs, etc."""
        self.ws.emit(Message("enclosure.system.reset"))

    def system_mute(self):
        """Mute (turn off) the system speaker."""
        self.ws.emit(Message("enclosure.system.mute"))

    def system_unmute(self):
        """Unmute (turn on) the system speaker."""
        self.ws.emit(Message("enclosure.system.unmute"))

    def system_blink(self, times):
        """The 'eyes' should blink the given number of times.
        Args:
            times (int): number of times to blink
        """
        self.ws.emit(Message("enclosure.system.blink", {'times': times}))

    def eyes_on(self):
        """Illuminate or show the eyes."""
        self.ws.emit(Message("enclosure.eyes.on"))

    def eyes_off(self):
        """Turn off or hide the eyes."""
        self.ws.emit(Message("enclosure.eyes.off"))

    def eyes_blink(self, side):
        """Make the eyes blink
        Args:
            side (str): 'r', 'l', or 'b' for 'right', 'left' or 'both'
        """
        self.ws.emit(Message("enclosure.eyes.blink", {'side': side}))

    def eyes_narrow(self):
        """Make the eyes look narrow, like a squint"""
        self.ws.emit(Message("enclosure.eyes.narrow"))

    def eyes_look(self, side):
        """Make the eyes look to the given side
        Args:
            side (str): 'r' for right
                        'l' for left
                        'u' for up
                        'd' for down
                        'c' for crossed
        """
        self.ws.emit(Message("enclosure.eyes.look", {'side': side}))

    def eyes_color(self, r=255, g=255, b=255):
        """Change the eye color to the given RGB color
        Args:
            r (int): 0-255, red value
            g (int): 0-255, green value
            b (int): 0-255, blue value
        """
        self.ws.emit(Message("enclosure.eyes.color",
                             {'r': r, 'g': g, 'b': b}))

    def eyes_brightness(self, level=30):
        """Set the brightness of the eyes in the display.
        Args:
            level (int): 1-30, bigger numbers being brighter
        """
        self.ws.emit(Message("enclosure.eyes.level", {'level': level}))

    def eyes_reset(self):
        """Restore the eyes to their default (ready) state."""
        self.ws.emit(Message("enclosure.eyes.reset"))

    def eyes_timed_spin(self, length):
        """Make the eyes 'roll' for the given time.
        Args:
            length (int): duration in milliseconds of roll, None = forever
        """
        self.ws.emit(Message("enclosure.eyes.timedspin",
                             {'length': length}))

    def eyes_volume(self, volume):
        """Indicate the volume using the eyes
        Args:
            volume (int): 0 to 11
        """
        self.ws.emit(Message("enclosure.eyes.volume", {'volume': volume}))

    def mouth_reset(self):
        """Restore the mouth display to normal (blank)"""
        self.ws.emit(Message("enclosure.mouth.reset"))
        DisplayManager.set_active(self.name)

    def mouth_talk(self):
        """Show a generic 'talking' animation for non-synched speech"""
        self.ws.emit(Message("enclosure.mouth.talk"))
        DisplayManager.set_active(self.name)

    def mouth_think(self):
        """Show a 'thinking' image or animation"""
        self.ws.emit(Message("enclosure.mouth.think"))
        DisplayManager.set_active(self.name)

    def mouth_listen(self):
        """Show a 'thinking' image or animation"""
        self.ws.emit(Message("enclosure.mouth.listen"))
        DisplayManager.set_active(self.name)

    def mouth_smile(self):
        """Show a 'smile' image or animation"""
        self.ws.emit(Message("enclosure.mouth.smile"))
        DisplayManager.set_active(self.name)

    def mouth_viseme(self, code):
        """Display a viseme mouth shape for synched speech
        Args:
            code (int):  0 = shape for sounds like 'y' or 'aa'
                         1 = shape for sounds like 'aw'
                         2 = shape for sounds like 'uh' or 'r'
                         3 = shape for sounds like 'th' or 'sh'
                         4 = neutral shape for no sound
                         5 = shape for sounds like 'f' or 'v'
                         6 = shape for sounds like 'oy' or 'ao'
        """
        self.ws.emit(Message("enclosure.mouth.viseme", {'code': code}))

    def mouth_text(self, text=""):
        """Display text (scrolling as needed)
        Args:
            text (str): text string to display
        """
        DisplayManager.set_active(self.name)
        self.ws.emit(Message("enclosure.mouth.text", {'text': text}))

    def mouth_display(self, img_code="", x=0, y=0, refresh=True):
        """Display images on faceplate. Currently supports images up to 16x8,
           or half the face. You can use the 'x' parameter to cover the other
           half of the faceplate.
        Args:
            img_code (str): text string that encodes a black and white image
            x (int): x offset for image
            y (int): y offset for image
            refresh (bool): specify whether to clear the faceplate before
                            displaying the new image or not.
                            Useful if you'd like to display muliple images
                            on the faceplate at once.
        """
        DisplayManager.set_active(self.name)
        self.ws.emit(Message('enclosure.mouth.display',
                             {'img_code': img_code,
                              'xOffset': x,
                              'yOffset': y,
                              'clearPrev': refresh}))

    def mouth_display_png(self, image_absolute_path, threshold=70,
                          invert=False, x=0, y=0, refresh=True):
        """Converts a png image into the appropriate encoding for the
            Arduino Mark I enclosure.

            NOTE: extract this out of api.py when re structuing the
                  enclosure folder

            Args:
                image_absolute_path (string): The absolute path of the image
                threshold (int): The value ranges from 0 to 255. The pixel will
                                 draw on the faceplate it the value is below a
                                 threshold
                invert (bool): inverts the image being drawn.
                x (int): x offset for image
                y (int): y offset for image
                refresh (bool): specify whether to clear the faceplate before
                                displaying the new image or not.
                                Useful if you'd like to display muliple images
                                on the faceplate at once.
            """
        DisplayManager.set_active(self.name)

        # to understand how this funtion works you need to understand how the
        # Mark I arduino proprietary encoding works to display to the faceplate
        img = Image.open(image_absolute_path).convert("RGBA")
        img2 = Image.new('RGBA', img.size, (255, 255, 255))
        width = img.size[0]
        height = img.size[1]

        # strips out alpha value and blends it with the RGB values
        img = Image.alpha_composite(img2, img)
        img = img.convert("L")

        # crop image to only allow a max width of 16
        if width > 32:
            img = img.crop((0, 0, 32, height))
            width = img.size[0]
            height = img.size[1]

        # crop the image to limit the max height of 8
        if height > 8:
            img = img.crop((0, 0, width, 8))
            width = img.size[0]
            height = img.size[1]

        encode = ""

        # Each char value represents a width number starting with B=1
        # then increment 1 for the next. ie C=2
        width_codes = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
                       'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
                       'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a']

        height_codes = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']

        encode += width_codes[width - 1]
        encode += height_codes[height - 1]

        # Turn the image pixels into binary values 1's and 0's
        # the Mark I face plate encoding uses binary values to
        # binary_values returns a list of 1's and 0s'. ie ['1', '1', '0', ...]
        binary_values = []
        for i in range(width):
            for j in range(height):
                if img.getpixel((i, j)) < threshold:
                    if invert is False:
                        binary_values.append('1')
                    else:
                        binary_values.append('0')
                else:
                    if invert is False:
                        binary_values.append('0')
                    else:
                        binary_values.append('1')

        # these values are used to determine how binary values
        # needs to be grouped together
        number_of_top_pixel = 0
        number_of_bottom_pixel = 0

        if height > 4:
            number_of_top_pixel = 4
            number_of_bottom_pixel = height - 4
        else:
            number_of_top_pixel = height

        # this loop will group together the individual binary values
        # ie. binary_list = ['1111', '001', '0101', '100']
        binary_list = []
        binary_code = ''
        increment = 0
        alternate = False
        for val in binary_values:
            binary_code += val
            increment += 1
            if increment == number_of_top_pixel and alternate is False:
                # binary code is reversed for encoding
                binary_list.append(binary_code[::-1])
                increment = 0
                binary_code = ''
                alternate = True
            elif increment == number_of_bottom_pixel and alternate is True:
                binary_list.append(binary_code[::-1])
                increment = 0
                binary_code = ''
                alternate = False

        # Code to let the Makrk I arduino know where to place the
        # pixels on the faceplate
        pixel_codes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                       'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']

        for binary_values in binary_list:
            number = int(binary_values, 2)
            pixel_code = pixel_codes[number]
            encode += pixel_code

        self.ws.emit(Message("enclosure.mouth.display",
                             {'img_code': encode,
                              'xOffset': x,
                              'yOffset': y,
                              'clearPrev': refresh}))

    def weather_display(self, img_code, temp):
        """Show a the temperature and a weather icon

        Args:
            img_code (char): one of the following icon codes
                         0 = sunny
                         1 = partly cloudy
                         2 = cloudy
                         3 = light rain
                         4 = raining
                         5 = stormy
                         6 = snowing
                         7 = wind/mist
            temp (int): the temperature (either C or F, not indicated)
        """
        DisplayManager.set_active(self.name)
        self.ws.emit(Message("enclosure.weather.display",
                             {'img_code': img_code, 'temp': temp}))

    def activate_mouth_events(self):
        """Enable movement of the mouth with speech"""
        self.ws.emit(Message('enclosure.mouth.events.activate'))

    def deactivate_mouth_events(self):
        """Disable movement of the mouth with speech"""
        self.ws.emit(Message('enclosure.mouth.events.deactivate'))
