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

import sys

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger

__author__ = 'aatchison'

LOGGER = getLogger("WiFiSetupClient")


class WiFi:
    def __init__(self):
        self.client = WebsocketClient()
        self.config = ConfigurationManager.get().get('WiFiClient')
        self.client.on('mycroft.wifi.start', self.start)
        self.first_setup()

    def first_setup(self):
        if self.config.get('must_start'):
            self.start()
            ConfigurationManager.set('WiFiClient', 'must_start', False)

    def start(self, event=None):
        self.client.emit(Message("speak", metadata={
            'utterance': "Initializing wireless setup mode."}))
        # ap_on()

    def run(self):
        try:
            self.client.run_forever()
        except Exception as e:
            LOGGER.error("Client error: {0}".format(e))
            self.stop()

    def stop(self):
        # TODO - STOP EVERYTHING!!!!
        pass


def main():
    wifi = WiFi()
    try:
        wifi.run()
    except Exception as e:
        print (e)
    finally:
        wifi.stop()
        sys.exit()


if __name__ == "__main__":
    main()
