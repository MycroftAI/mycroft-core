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


from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOG = getLogger(__name__)


class EnclosureMouth:
    """
    Listens to enclosure commands for Mycroft's Mouth.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, ws, writer):
        self.ws = ws
        self.writer = writer
        self.__init_events()

    def __init_events(self):
        self.ws.on('enclosure.mouth.reset', self.reset)
        self.ws.on('enclosure.mouth.talk', self.talk)
        self.ws.on('enclosure.mouth.think', self.think)
        self.ws.on('enclosure.mouth.listen', self.listen)
        self.ws.on('enclosure.mouth.smile', self.smile)
        self.ws.on('enclosure.mouth.viseme', self.viseme)
        self.ws.on('enclosure.mouth.text', self.text)

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
            if code:
                self.writer.write("mouth.viseme=" + code)

    def text(self, event=None):
        text = ""
        if event and event.data:
            text = event.data.get("text", text)
        self.writer.write("mouth.text=" + text)
