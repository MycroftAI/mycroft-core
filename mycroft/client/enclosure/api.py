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


from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


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

    def __init__(self, ws):
        self.ws = ws

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
        """Turn off the system microphone (not listening for wakeword)."""
        self.ws.emit(Message("enclosure.system.mute"))

    def system_unmute(self):
        """Turn the system microphone on (listening for wakeword)."""
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

    def mouth_talk(self):
        """Show a generic 'talking' animation for non-synched speech"""
        self.ws.emit(Message("enclosure.mouth.talk"))

    def mouth_think(self):
        """Show a 'thinking' image or animation"""
        self.ws.emit(Message("enclosure.mouth.think"))

    def mouth_listen(self):
        """Show a 'thinking' image or animation"""
        self.ws.emit(Message("enclosure.mouth.listen"))

    def mouth_smile(self):
        """Show a 'smile' image or animation"""
        self.ws.emit(Message("enclosure.mouth.smile"))

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
        self.ws.emit(Message("enclosure.mouth.text", {'text': text}))

    def weather_display(self, img_code, temp):
        """Show a weather icon (deprecated)"""
        self.ws.emit(Message("enclosure.weather.display",
                             {'img_code': img_code, 'temp': temp}))

    def activate_mouth_events(self):
        """Enable movement of the mouth with speech"""
        self.ws.emit(Message('enclosure.mouth.events.activate'))

    def deactivate_mouth_events(self):
        """Disable movement of the mouth with speech"""
        self.ws.emit(Message('enclosure.mouth.events.deactivate'))
