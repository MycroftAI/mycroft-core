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
import time

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class EnclosureMouth:
    """
    Listens to enclosure commands for Mycroft's Mouth.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, client, writer):
        self.client = client
        self.writer = writer
        self.__init_events()

    def __init_events(self):
        self.client.on('enclosure.mouth.reset', self.reset)
        self.client.on('enclosure.mouth.talk', self.talk)
        self.client.on('enclosure.mouth.think', self.think)
        self.client.on('enclosure.mouth.listen', self.listen)
        self.client.on('enclosure.mouth.smile', self.smile)
        self.client.on('enclosure.mouth.viseme', self.viseme)
        self.client.on('enclosure.mouth.text', self.text)

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
        visCmds = ''
        if event and event.metadata:
            visCmds = event.metadata.get("code", visCmds)
            # visCmds will be string of viseme codes and cumulative durations
            # ex:  '0:0.34,1:1.23,0:1.32,'
            lisPairs = visCmds.split(",")
            timeStart = time.time()
            for pair in lisPairs:
                vis_dur = pair.split(":")
                if vis_dur[0] >= "0" and vis_dur[0] <= "6":
                    elap = time.time() - timeStart
                    self.writer.write("mouth.viseme=" + vis_dur[0])
                    if elap < float(vis_dur[1]):
                        time.sleep(float(vis_dur[1]) - elap)

    def text(self, event=None):
        text = ""
        if event and event.metadata:
            text = event.metadata.get("text", text)
        self.writer.write("mouth.text=" + text)
