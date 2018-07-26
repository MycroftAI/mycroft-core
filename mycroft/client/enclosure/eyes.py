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

    def on(self):
        self.writer.write("eyes.on")

    def off(self):
        self.writer.write("eyes.off")

    def blink(self, side="b"):
        self.writer.write("eyes.blink=" + side)

    def narrow(self):
        self.writer.write("eyes.narrow")

    def look(self, side=""):
        self.writer.write("eyes.look=" + side)

    def color(self, color=(255 * 65536) + (255 * 256) + 255):
        self.writer.write("eyes.color=" + str(color))

    def set_pixel(self, idx, color):
        self.writer.write("eyes.set=" + str(idx) + "," + str(color))

    def fill(self, amount=0):
        self.writer.write("eyes.fill=" + str(amount))

    def brightness(self, level=30):
        self.writer.write("eyes.level=" + str(level))

    def volume(self, volume=4):
        self.writer.write("eyes.volume=" + str(volume))

    def reset(self):
        self.writer.write("eyes.reset")

    def spin(self):
        self.writer.write("eyes.spin")

    def timed_spin(self, length=5000):
        self.writer.write("eyes.spin=" + str(length))
