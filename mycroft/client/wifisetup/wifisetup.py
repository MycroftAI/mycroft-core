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
import os
import threading
import tornado.ioloop
import tornado.template
import tornado.web
import tornado.websocket

from Queue import Queue
from threading import Thread, Lock
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import str2bool
from mycroft.util.log import getLogger

from mycroft.client.wifisetup.app.util.Server import MainHandler,\
    WSHandler, JSHandler, BootstrapMinJSHandler, BootstrapMinCSSHandler,\
    ap_on

__author__ = 'aatchison'

client = None
mutex = Lock()

LOGGER = getLogger("WiFiSetupClient")

queueLock = threading.Lock()
workQueue = Queue(10)
threads = []
threadID = 1


class TornadoWorker (threading.Thread):
    """
        Creates a thread handler and initializes two tornado instances
    """
    def __init__(self, threadID, name, http_port, ws_port, q):
        root = os.path.join(os.path.dirname(__file__), "srv/templates")
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
        self.handlers = [
            (r"/", MainHandler),
            (r"/jquery-2.2.3.min.js", JSHandler),
            (r"/img/(.*)", tornado.web.StaticFileHandler,
             {'path': os.path.join(root, 'img/')}),
            (r"/bootstrap-3.3.7-dist/css/bootstrap.min.css",
             BootstrapMinCSSHandler),
            (r"/bootstrap-3.3.7-dist/js/bootstrap.min.js",
             BootstrapMinJSHandler),
            (r"/ws", WSHandler)]
        self.settings = dict(
            template_path=os.path.join(
                os.path.dirname(__file__), "./srv/templates"),)
        self.http_port = http_port
        self.ws_port = ws_port
        self.ws_app = tornado.web.Application([(r'/ws', WSHandler), ])
        self.http_app = tornado.web.Application(self.handlers, **self.settings)

    def run(self):
        LOGGER.info(
            "Starting Thread " +
            self.name + " " +
            str(self.threadID) +
            " with: http_port: " +
            self.http_port + " ws_port:" + self.ws_port)
        self.ws_app.listen(self.ws_port)
        self.http_app.listen(self.http_port)
        tornado.ioloop.IOLoop.current().start()
        LOGGER.info("Exiting " + self.name)

    def stop(self):
        self.alive = False
        self.join()


class WiFi:
    def __init__(self):
        self.client = WebsocketClient()
        self.reader = WiFiSocketReader(self.client)
        self.config = ConfigurationManager.get().get('WiFiClient')
        self.alive = True

    def run(self):
        self.client.run_forever()

    def setup(self):
        must_start = self.config.get('must_start')
        if must_start is not None and str2bool(must_start) is True:
            LOGGER.info("Initialising wireless setup mode.")
            ConfigurationManager.set('WiFiClient', 'must_start', False)
        else:
            "First run is false"

    def stop(self, event=None):
        self.alive = False
        self.join()


class WiFiSocketReader(Thread):
    def __init__(self, client):
        super(WiFiSocketReader, self).__init__(target=self.run)
        self.config = ConfigurationManager.get().get('WiFiClient')
        self.ws_port = self.config.get('ws_port')
        self.http_port = self.config.get('http_port')

        self.client = client
        self.alive = True
        self.daemon = True
        self.client.on('wifisetup.start', self.up)
        self.client.on('wifisetup.start', self.__init_tornado)

    def run(self):
        while self.alive is True:
            try:
                self.client.run_forever()
            except Exception as e:
                LOGGER.error("Client error: {0}".format(e))
                self.stop()

    def stop(self):
        self.alive = False
        self.join()

    def __init_tornado(self, envent=None):
        try:
            TornadoWorker(
                1, "http+ws", self.ws_port, self.http_port, 0).start()
            LOGGER.info("Web Server Initialized")

        except Exception as e:
            LOGGER.warn(e)
        finally:
            sys.exit()

    def up(self, event=None):
        self.client.emit(Message("speak", metadata={
            'utterance': "Initializing wireless setup mode."}))
        ap_on()


def main():
    try:
        wifi = WiFi()
        t = Thread(target=wifi.run)
        t.start()
        wifi.setup()
        t.join()
    except Exception as e:
        print (e)
    finally:
        sys.exit()

if __name__ == "__main__":
    main()
