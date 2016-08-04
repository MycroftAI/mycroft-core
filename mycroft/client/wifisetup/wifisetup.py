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
import subprocess
import sys
from Queue import Queue
from alsaaudio import Mixer
from threading import Thread

import os
import datetime
import tornado.ioloop
import tornado.web, tornado.websocket
import tornado.template

import os
import serial
import time

import threading
from mycroft.client.wifisetup.webserver import MainHandler
from mycroft.client.wifisetup.webserver import WSHandler
from mycroft.client.wifisetup.webserver import JSHandler
from mycroft.client.wifisetup.Config import AppConfig
#from mycroft.client.enclosure.eyes import EnclosureEyes
#from mycroft.client.enclosure.mouth import EnclosureMouth
#from mycroft.client.enclosure.weather import EnclosureWeather
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import kill, str2bool
from mycroft.util import play_wav
from mycroft.util.log import getLogger
from mycroft.util.audio_test import record

__author__ = 'aatchison + jdorleans + iward'

LOGGER = getLogger("EnclosureClient")


class WiFiSetup(Thread):

    def run(self):
        try:
            self.client.run_forever()
        except Exception as e:
            LOGGER.error("Client error: {0}".format(e))
            self.stop()

    def stop(self):
        self.writer.stop()
        self.reader.stop()
        self.serial.close()

handlers = [
    (r"/", MainHandler),
    (r"/jquery-2.2.3.min.js",JSHandler),
    (r"/ws",WSHandler),
]

settings = dict(
    template_path=os.path.join(os.path.dirname(__file__), "srv/templates"),
)
wifi_connection_settings = {'ssid':'', 'passphrase':''}

def main():
        config = AppConfig()
        config.open_file()
        Port = config.ConfigSectionMap("server_port")['port']
        WSPort = config.ConfigSectionMap("server_port")['ws_port']
        print Port
        ws_app = tornado.web.Application([(r'/ws', WSHandler), ])
        ws_app.listen(Port)
        app = threading.Thread(target=tornado.web.Application(handlers, **settings))
        tornado.ioloop.IOLoop.current().start()
        web_main_handler = MainHandler()
        web_js_handler = JSHandler()
        try:
            app.start()
            enclosure.setup()
            app.join()
        except Exception as e:
            print(e)
        finally:
            sys.exit()
            print "ok"


if __name__ == "__main__":
    main()
