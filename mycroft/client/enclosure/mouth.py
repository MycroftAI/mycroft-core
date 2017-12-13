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
from mycroft.enclosure import Enclosure


class EnclosureMouth(Enclosure):
    """
    Listens to enclosure commands for Mycroft's Mouth.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, ws, writer):
        super(EnclosureMouth, self).__init__(ws, "mouth")
        self.writer = writer
        self.is_timer_on = False

    def mouth_reset(self, message=None):
        self.writer.write("mouth.reset")

    def mouth_talk(self, message=None):
        self.writer.write("mouth.talk")

    def mouth_think(self, message=None):
        self.writer.write("mouth.think")

    def mouth_listen(self, message=None):
        self.writer.write("mouth.listen")

    def mouth_smile(self, message=None):
        self.writer.write("mouth.smile")

    def mouth_viseme(self, message=None):
        if message and message.data:
            code = message.data.get("code")
            time_until = message.data.get("until")
            # Skip the viseme if the time has expired.  This helps when a
            # system glitch overloads the bus and throws off the timing of
            # the animation timing.
            if code and (not time_until or time.time() < time_until):
                self.writer.write("mouth.viseme=" + code)

    def mouth_text(self, message=None):
        text = ""
        if message and message.data:
            text = message.data.get("text", text)
        self.writer.write("mouth.text=" + text)

    def mouth_display(self, message=None):
        code = ""
        xOffset = ""
        yOffset = ""
        clearPrevious = ""
        if message and message.data:
            code = message.data.get("img_code", code)
            xOffset = int(message.data.get("xOffset", xOffset))
            yOffset = int(message.data.get("yOffset", yOffset))
            clearPrevious = message.data.get("clearPrev", clearPrevious)

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
