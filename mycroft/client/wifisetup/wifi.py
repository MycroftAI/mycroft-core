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

__author__ = 'aatchison'

from Queue import Queue
from threading import Thread
# mycroft stuff
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import str2bool
from mycroft.util.log import getLogger
# wifi setup stuff
import sys
import os
import threading
import Queue
from mycroft.client.wifisetup.app.util.Server import MainHandler, WSHandler, JSHandler, BootstrapMinJSHandler, BootstrapMinCSSHandler
# web server stuff
import tornado.ioloop
import tornado.template
import tornado.web
import tornado.websocket
from mycroft.client.wifisetup.app.util.WiFiTools import ap_link_tools
from mycroft.client.wifisetup.app.util.FileUtils import ap_mode_config, write_hostapd_conf, write_network_interfaces, write_dnsmasq
from mycroft.client.wifisetup.app.util.LinkUtils import ScanForAP, link_add_vap
from mycroft.client.wifisetup.app.util.WiFiTools import ap_link_tools,dev_link_tools, hostapd_tools
from mycroft.client.wifisetup.app.util.dnsmasqTools import dnsmasqTools
from mycroft.client.wifisetup.app.util.hostAPDTools import hostAPServerTools
from mycroft.client.wifisetup.app.util.Server import MainHandler, JSHandler, BootstrapMinJSHandler, BootstrapMinCSSHandler, WSHandler
from mycroft.client.wifisetup.app.util.wpaCLITools import wpaClientTools


# use config file for these
client_iface = 'wlan0'
ap_iface = 'uap0'
ap_iface_ip = '172.24.1.1'
ap_iface_ip_range_start = '172.24.1.10'
ap_iface_ip_range_end = '172.24.1.20'
ap_iface_mac = 'bc:5f:f4:be:7d:0a'
http_port = '8888'
ws_port = '8080'

dev_link_tools = dev_link_tools(client_iface)
linktools = ap_link_tools()


LOGGER = getLogger("WiFiSetupClient")

# web vars

nameList = ['web','ap', 'dns']
queueLock = threading.Lock()
workQueue = Queue.Queue(10)
threads = []
threadID = 1


class WiFiSetup(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
        self.__init_wifi_setup()
        self.client = WebsocketClient()
        self.__register_wifi_events()

    def setup(self):
        must_start_ap_mode = self.config.get(str2bool('must_start_ap_mode'))
        if must_start_ap_mode is not None and must_start_ap_mode is True:
            LOGGER.info("Initalizing wireless setup mode.")
            self.client.emit(Message("speak", metadata={
                'utterance': "Initializing wireless setup mode."}))

    def run(self):
        try:
            self.client.run_forever()
            #self.__init_tornado()
        except Exception as e:
            LOGGER.error("Client error: {0}".format(e))
            self.stop()

    def stop(self):
        LOGGER.info("Shut down wireless setup mode.")


    def __register_events(self):
        self.client.on('recognizer_loop:record_begin', self.__update_events)
        self.__register_wifi_events()


    def __wifi_listeners(self, event=None):
        if event and event.metadata:
            active = event.metadata['active']
            if active:
                self.__register_wifi_events()
            else:
                self.__remove_wifi_events()


    def __register_wifi_events(self):
        self.client.on('recognizer_loop:record_begin',self.__init_tornado())

    def __remove_wifi_events(self):
        self.client.remove('recognizer_loop:record_begin', self.__init_tornado())

    def __update_events(self, event=None):
        if event and event.metadata:
            if event.metadata.get('paired', False):
                self.__register_wifi_events()
            else:
                self.__remove_wifi_events()

    def __init_wifi_setup(self):
        self.config = ConfigurationManager.get().get("WiFiClient")

    def __init_tornado(self):
        try:
            TornadoWorker(1, "http+ws", ws_port, http_port,0 ).start()
            LOGGER.info("Web Server Initialized")
        except Exception as e:
            LOGGER.warn(e)
        finally:
            sys.exit()


class TornadoWorker (threading.Thread):
    """
        Creates a thread landler and initializes two tornado instances
    """
    def __init__(self, threadID, name, http_port, ws_port, q):
        root = os.path.join(os.path.dirname(__file__), "srv/templates")
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
        self.handlers = [
            (r"/", MainHandler),
            (r"/jquery-2.2.3.min.js",JSHandler),
            (r"/img/(.*)", tornado.web.StaticFileHandler, { 'path': os.path.join(root, 'img/') } ),
            (r"/bootstrap-3.3.7-dist/css/bootstrap.min.css",BootstrapMinCSSHandler),
            (r"/bootstrap-3.3.7-dist/js/bootstrap.min.js",BootstrapMinJSHandler),
            (r"/ws",WSHandler)]
        self.settings = dict(template_path=os.path.join(os.path.dirname(__file__), "./srv/templates"),)
        self.http_port = http_port
        self.ws_port = ws_port
        self.ws_app = tornado.web.Application([(r'/ws', WSHandler), ])
        self.http_app = tornado.web.Application(self.handlers, **self.settings)

    def run(self):
        LOGGER.info( "Starting Thread " + self.name + " " +str(self.threadID) +
                     " with: http_port: " + self.http_port +
                     " ws_port:"+ self.ws_port)
        self.ws_app.listen(self.ws_port)
        self.http_app.listen(self.http_port)
        tornado.ioloop.IOLoop.current().start()
        LOGGER.info( "Exiting " + self.name)


class ApWorker(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        LOGGER.info( "Starting " + self.name + " " + str(self.threadID))
        apScan = ScanForAP('scan', client_iface)
        apScan.start()
        apScan.join()
        ap = apScan.join()


        try:
            #self.station_mode_on()
            LOGGER.info("station on")
        except:
            self._return = exit(0)

    def station_mode_on(self):
        LOGGER.info("station mode on")
        ap_mode_config()
        print init_stop_services()
        time.sleep(2)
        print init_set_interfaces()
        time.sleep(2)
        print init_hostap_mode()
        # self.aptools.hostapd_start()
        # self.aptools.dnsmasq_start()
        # aptools.ap_config()
        # SSP: Temporary change while developing
        #        AP.copy_config_ap()
        #        devtools.link_down()
        #        aptools.ap_up()

    def station_mode_off(self):
        LOGGER.info("station mode off")
        self.aptools.dnsmasq_stop()
        self.aptools.hostapd_stop()

    def dnsmasq_on(self):
        self.aptools.dnsmasq_start()

    def dnsmasq_off(self):
        self.aptools.dnsmasq_stop()

    # SSP: Temporary change while developing
    #        aptools.ap_down()
    #        aptools.ap_deconfig()
    #        devtools.link_down()
    #        devtools.link_up()

    def join(self, timeout=None):
           threading.Thread.join(self, timeout=self.timeout)
           return self._return()


class dnsmasqWorker (threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        LOGGER.info("Starting " + self.name + str(self.threadID))

        try:
            LOGGER.info("dnsmasq on")
            S.dnsmasq_on()
        except:
            exit(0)


def init_stop_services():
    WPATools.wpa_cli_flush()
    DNSTools.dnsmasqServiceStop()
    APTools.hostAPDStop()
    LOGGER.info("STOPPED: services")


def init_set_interfaces():
    write_network_interfaces(client_iface, ap_iface, ap_iface, ap_iface_mac)
    link_add_vap()
    LOGGER.info("SETUP: interfaces")


def init_hostap_mode():
    write_hostapd_conf(ap_iface,'nl80211','mycroft',11)
    write_dnsmasq(
        ap_iface, ap_iface_ip, ap_iface_ip_range_start, ap_iface_ip_range_end)
    APTools.hostAPDStart()
    DNSTools.dnsmasqServiceStart()
    return APTools.hostAPDStatus()


def try_connect():
    network_id = WPATools.wpa_cli_add_network(ap_iface)
    print network_id
    # print wpa_cli_flush()
    print WPATools.wpa_cli_set_network(client_iface, '0', 'ssid', '"Entrepreneur"')
    print WPATools.wpa_cli_set_network(client_iface, '0', 'psk', '"startsomething"')
    print WPATools.wpa_cli_enable_network(client_iface, '0')


def exit_gracefully(signal, frame):
    INIT = False
    print "caught SIGINT"
    S = Station()
    # ap_mode_deconfig()
    S.station_mode_off()
    S.dnsmasq_off()
    print "exiting"
    sys.exit(0)


def main():
    try:
        wifi_setup = WiFiSetup(1, 'wifi', 0)
        wifi_setup.start()
        wifi_setup.join()
        # t = TornadoWorker(1, 'http+ws', '8081', '8888' , 0)
        # t.start()
        # t.join()

    except Exception as e:
        print (e)
    finally:
        sys.exit()

if __name__ == "__main__":
    main()
