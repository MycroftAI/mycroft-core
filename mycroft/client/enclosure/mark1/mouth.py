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
from PIL import Image


class EnclosureMouth:
    """
    Listens to enclosure commands for Mycroft's Mouth.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, bus, writer):
        self.bus = bus
        self.writer = writer
        self.is_timer_on = False
        self.__init_events()
        self.showing_visemes = False

    def __init_events(self):
        self.bus.on('enclosure.mouth.reset', self.reset)
        self.bus.on('enclosure.mouth.talk', self.talk)
        self.bus.on('enclosure.mouth.think', self.think)
        self.bus.on('enclosure.mouth.listen', self.listen)
        self.bus.on('enclosure.mouth.smile', self.smile)
        self.bus.on('enclosure.mouth.viseme_list', self.viseme_list)
        self.bus.on('enclosure.mouth.text', self.text)
        self.bus.on('enclosure.mouth.display', self.display)
        self.bus.on('enclosure.mouth.display_image', self.display_image)
        self.bus.on('enclosure.weather.display', self.display_weather)
        self.bus.on('mycroft.stop', self.clear_visemes)
        self.bus.on('enclosure.mouth.events.activate',
                    self._activate_visemes)
        self.bus.on('enclosure.mouth.events.deactivate',
                    self._deactivate_visemes)

    def _activate_visemes(self, event=None):
        self.bus.on('enclosure.mouth.viseme_list', self.viseme_list)

    def _deactivate_visemes(self, event=None):
        self.bus.remove('enclosure.mouth.viseme_list', self.viseme_list)

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

    def viseme_list(self, event=None):
        if event and event.data:
            start = event.data['start']
            visemes = event.data['visemes']
            self.showing_visemes = True
            for code, end in visemes:
                if not self.showing_visemes:
                    break
                if time.time() < start + end:
                    self.writer.write('mouth.viseme=' + code)
                    time.sleep(start + end - time.time())
            self.reset()

    def clear_visemes(self, event=None):
        self.showing_visemes = False

    def text(self, event=None):
        text = ""
        if event and event.data:
            text = event.data.get("text", text)
        self.writer.write("mouth.text=" + text)

    def __display(self, code, clear_previous, x_offset, y_offset):
        """ Write the encoded image to enclosure screen.

        Arguments:
            code (str):           encoded image to display
            clean_previous (str): if "True" will clear the screen before
                                  drawing.
            x_offset (int):       x direction offset
            y_offset (int):       y direction offset
        """
        clear_previous = int(str(clear_previous) == "True")
        clear_previous = "cP=" + str(clear_previous) + ","
        x_offset = "x=" + str(x_offset) + ","
        y_offset = "y=" + str(y_offset) + ","

        message = "mouth.icon=" + x_offset + y_offset + clear_previous + code
        # Check if message exceeds Arduino's serial buffer input limit 64 bytes
        if len(message) > 60:
            message1 = message[:31] + "$"
            message2 = "mouth.icon=$" + message[31:]
            self.writer.write(message1)
            time.sleep(0.25)  # writer bugs out if sending messages too rapidly
            self.writer.write(message2)
        else:
            time.sleep(0.1)
            self.writer.write(message)

    def display(self, event=None):
        """ Display a Mark-1 specific code.
        Arguments:
            event (Message): messagebus message with data to display
        """
        code = ""
        x_offset = ""
        y_offset = ""
        clear_previous = ""
        if event and event.data:
            code = event.data.get("img_code", code)
            x_offset = int(event.data.get("xOffset", x_offset))
            y_offset = int(event.data.get("yOffset", y_offset))
            clear_previous = event.data.get("clearPrev", clear_previous)
            self.__display(code, clear_previous, x_offset, y_offset)

    def display_image(self, event=None):
        """ Display an image on the enclosure.

        The method uses PIL to convert the image supplied into a code
        suitable for the Mark-1 display.

        Arguments:
            event (Message): messagebus message with data to display
        """
        if not event:
            return

        image_absolute_path = event.data['img_path']
        refresh = event.data['clearPrev']
        invert = event.data['invert']
        x_offset = event.data['xOffset']
        y_offset = event.data['yOffset']
        threshold = event.data.get('threshold', 70)  # default threshold
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

        self.__display(encode, refresh, x_offset, y_offset)

    def display_weather(self, event=None):
        if event and event.data:
            # Convert img_code to icon
            img_code = event.data.get("img_code", None)
            icon = None
            if img_code == 0:
                # sunny
                icon = "IICEIBMDNLMDIBCEAA"
            elif img_code == 1:
                # partly cloudy
                icon = "IIEEGBGDHLHDHBGEEA"
            elif img_code == 2:
                # cloudy
                icon = "IIIBMDMDODODODMDIB"
            elif img_code == 3:
                # light rain
                icon = "IIMAOJOFPBPJPFOBMA"
            elif img_code == 4:
                # raining
                icon = "IIMIOFOBPFPDPJOFMA"
            elif img_code == 5:
                # storming
                icon = "IIAAIIMEODLBJAAAAA"
            elif img_code == 6:
                # snowing
                icon = "IIJEKCMBPHMBKCJEAA"
            elif img_code == 7:
                # wind/mist
                icon = "IIABIBIBIJIJJGJAGA"

            temp = event.data.get("temp", None)
            if icon is not None and temp is not None:
                icon = "x=2," + icon
                msg = "weather.display=" + str(temp) + "," + str(icon)
                self.writer.write(msg)
