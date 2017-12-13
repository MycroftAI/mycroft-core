# Copyright 2017 Mycroft AI Inc.
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


class EnclosureEyes(object):
    """
    Listens to enclosure commands for Mycroft's Eyes.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, writer):
        self.writer = writer
        self.__init_events()

    def __init_events(self):
        self.ws.on('enclosure.eyes.on', self.on)
        self.ws.on('enclosure.eyes.off', self.off)
        self.ws.on('enclosure.eyes.blink', self.blink)
        self.ws.on('enclosure.eyes.narrow', self.narrow)
        self.ws.on('enclosure.eyes.look', self.look)
        self.ws.on('enclosure.eyes.color', self.color)
        self.ws.on('enclosure.eyes.level', self.brightness)
        self.ws.on('enclosure.eyes.volume', self.volume)
        self.ws.on('enclosure.eyes.spin', self.spin)
        self.ws.on('enclosure.eyes.timedspin', self.timed_spin)
        self.ws.on('enclosure.eyes.reset', self.reset)
        self.ws.on('enclosure.eyes.setpixel', self.set_pixel)
        self.ws.on('enclosure.eyes.fill', self.fill)

    def on(self):
        self.writer.write("eyes.on")

    def off(self):
        self.writer.write("eyes.off")

    def blink(self, side = "b"):
        self.writer.write("eyes.blink=" + side)

    def narrow(self):
        self.writer.write("eyes.narrow")

    def look(self, side=""):
        self.writer.write("eyes.look=" + side)

    def color(self, color=(255 * 65536) + (255 * 256) + 255):
        self.writer.write("eyes.color=" + str(color))

    def set_pixel(self, event=None):
        idx = 0
        r, g, b = 255, 255, 255
        if event and event.data:
            idx = int(event.data.get("idx", idx))
            r = int(event.data.get("r", r))
            g = int(event.data.get("g", g))
            b = int(event.data.get("b", b))
        color = (r * 65536) + (g * 256) + b
        self.writer.write("eyes.set=" + str(idx) + "," + str(color))

    def fill(self, event=None):
        amount = 0
        if event and event.data:
            percent = int(event.data.get("percentage", 0))
            amount = int(round(23.0 * percent / 100.0))
        self.writer.write("eyes.fill=" + str(amount))

    def brightness(self, message=None):
        level = 30
        if message and message.data:
            level = message.data.get("level", level)
        self.writer.write("eyes.level=" + str(level))

    def volume(self, volume=4):
        self.writer.write("eyes.volume=" + str(volume))

    def reset(self):
        self.writer.write("eyes.reset")

    def spin(self):
        self.writer.write("eyes.spin")

    def timed_spin(self, length=5000):
        self.writer.write("eyes.spin=" + str(length))
