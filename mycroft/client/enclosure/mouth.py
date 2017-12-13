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
#
import time


class EnclosureMouth(object):
    """
    Listens to enclosure commands for Mycroft's Mouth.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, writer):
        self.writer = writer
        self.is_timer_on = False

    def reset(self):
        self.writer.write("mouth.reset")

    def talk(self):
        self.writer.write("mouth.talk")

    def think(self):
        self.writer.write("mouth.think")

    def listen(self):
        self.writer.write("mouth.listen")

    def smile(self):
        self.writer.write("mouth.smile")

    def viseme(self, code, time_until):
        # Skip the viseme if the time has expired.  This helps when a
        # system glitch overloads the bus and throws off the timing of
        # the animation timing.
        if code and (not time_until or time.time() < time_until):
            self.writer.write("mouth.viseme=" + code)

    def text(self, text=""):
        self.writer.write("mouth.text=" + text)

    def display(self, code="", xOffset="", yOffset="", clearPrevious=""):
        clearPrevious = int(str(clearPrevious) == "True")
        clearPrevious = "cP=" + str(clearPrevious) + ","
        x_offset = "x=" + str(xOffset) + ","
        y_offset = "y=" + str(yOffset) + ","

        message = "mouth.icon=" + x_offset + y_offset + clearPrevious + code
        # Check if message exceeds Arduino's serial buffer input limit 64 bytes
        if len(message) > 60:
            message1 = message[:31]
            message2 = message[31:]
            message1 += "$"
            message2 += "$"
            message2 = "mouth.icon=" + message2
            self.writer.write(message1)
            time.sleep(0.25)  # writer bugs out if sending messages too rapidly
            self.writer.write(message2)
        else:
            time.sleep(0.1)
            self.writer.write(message)
