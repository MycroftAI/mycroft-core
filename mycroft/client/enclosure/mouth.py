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


class EnclosureMouth:
    """
    Listens to enclosure commands for Mycroft's Mouth.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, ws, writer):
        self.ws = ws
        self.writer = writer
        self.is_timer_on = False
        self.__init_events()

    def __init_events(self):
        self.ws.on('enclosure.mouth.reset', self.reset)
        self.ws.on('enclosure.mouth.talk', self.talk)
        self.ws.on('enclosure.mouth.think', self.think)
        self.ws.on('enclosure.mouth.listen', self.listen)
        self.ws.on('enclosure.mouth.smile', self.smile)
        self.ws.on('enclosure.mouth.viseme', self.viseme)
        self.ws.on('enclosure.mouth.text', self.text)
        self.ws.on('enclosure.mouth.display', self.display)

    def reset(self, event=None):
        self.writer.write("mouth.reset")

    def talk(self, event=None):
        self.writer.write("mouth.talk")

    def think(self, event=None):
        self.writer.write("mouth.think")

    def listen(self, event=None):
        self.writer.write("mouth.listen")

    def smile(self, event=None):
        self.writer.write("mouth.smile")

    def viseme(self, event=None):
        if event and event.data:
            code = event.data.get("code")
            time_until = event.data.get("until")
            # Skip the viseme if the time has expired.  This helps when a
            # system glitch overloads the bus and throws off the timing of
            # the animation timing.
            if code and (not time_until or time.time() < time_until):
                self.writer.write("mouth.viseme=" + code)

    def text(self, event=None):
        text = ""
        if event and event.data:
            text = event.data.get("text", text)
        self.writer.write("mouth.text=" + text)

    def display(self, event=None):
        code = ""
        xOffset = ""
        yOffset = ""
        clearPrevious = ""
        if event and event.data:
            code = event.data.get("img_code", code)
            xOffset = int(event.data.get("xOffset", xOffset))
            yOffset = int(event.data.get("yOffset", yOffset))
            clearPrevious = event.data.get("clearPrev", clearPrevious)

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
