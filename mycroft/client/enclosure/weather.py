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

__author__ = 'iward'

LOGGER = getLogger(__name__)


class EnclosureWeather:
    """
    Listens to enclosure commands to display indicators of the weather.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, client, writer):
        self.client = client
        self.writer = writer
        self.__init_events()

    def __init_events(self):
        self.client.on('enclosure.weather.display', self.display)

    def display(self, event=None):
        if event and event.data:
            img_code = event.data.get("img_code", None)
            temp = event.data.get("temp", None)
            if img_code is not None and temp is not None:
                msg = "weather.display=" + str(img_code) + str(temp)
                self.writer.write(msg)
