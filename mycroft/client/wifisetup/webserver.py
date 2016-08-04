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
import os
import datetime
import tornado.ioloop
import tornado.web, tornado.websocket
import tornado.template
from threading import Thread
from Config import AppConfig



from mycroft.util.log import getLogger

__author__ = 'aatchison'

LOGGER = getLogger(__name__)


class WifiSetupWeb:
    """
    Create a tornado server to display the We-Fi setup page.
    """

    def __init__(self, client, writer):
        self.client = client
        self.writer = writer
        self.__init_events()

    def __init_events(self):
        self.client.on('enclosure.weather.display', self.display)

    def display(self, event=None):
        if event and event.metadata:
            img_code = event.metadata.get("img_code", None)
            temp = event.metadata.get("temp", None)
            if img_code is not None and temp is not None:
                msg = "weather.display=" + str(img_code) + str(temp)
                self.writer.write(msg)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        print "page loaded", datetime.datetime.now()
        self.render("index.html",
                    ap=ap)
class JSHandler(tornado.web.RequestHandler):
    def get(self):
        print "request for jquery", datetime.datetime.now()
        self.render("jquery-2.2.3.min.js")

class WSHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self,origin):
        return True
    def open(self):
        print 'user is connected'

    def on_message(self, message):
        print 'received message: %s\n' % message
        self.write_message(message + ' OK')
        message_switch(message)

    def on_close(self):
        print 'connection closed\n'

handlers = [
    (r"/", MainHandler),
    (r"/jquery-2.2.3.min.js",JSHandler),
    (r"/ws",WSHandler),
]

settings = dict(
    template_path=os.path.join(os.path.dirname(__file__), "srv/templates"),
)
wifi_connection_settings = {'ssid':'', 'passphrase':''}

class station(Thread):
    def station_mode_on(self):
        print "station mode on"
        #aptools.ap_config()
        #AP.copy_config_ap()
        #devtools.link_down()
        #aptools.ap_up()

    def station_mode_off(self):
        print "station mode off"
        #aptools.ap_down()
        #aptools.ap_deconfig()
        #devtools.link_down()
        #devtools.link_up()

def connect_to_wifi(ssid,passphrase):
    print " connecting to wifi:", ssid, passphrase

def message_switch(message):
    dict2 = ast.literal_eval(message)
    print type(dict2)
    if is_match("'ap_on'", message) is True:
        station_mode_on()
    elif is_match("'ap_off'", message) is True:
        station_mode_off()
    elif is_match("'scan_networks'", message) is True:
        print "Need: Refresh page/div/unhide/something"
    elif is_match("'ssid'", message) is True:
        print "SSID selected: ", dict2['ssid']
        wifi_connection_settings['ssid'] = dict2['ssid']
    elif is_match("'passphrase'",message) is True:
        print "PASSPHRASE Recieved:", dict2
        print dict2['passphrase']
        S.station_mode_off()
        wifi_connection_settings['passphrase'] = dict2['passphrase']
        connect_to_wifi(wifi_connection_settings['ssid'],dict2['passphrase'])
#        time.sleep(5)

def is_match(regex, text):
    pattern = re.compile(regex)
    return pattern.search(text) is not None


if __name__ == "__main__":
    # APTools setup
    #AP = APConfig()
    #AP.ssid = 'Mycroft' + '-' + str(get_mac())
    #AP.copy_config_ap()
    #APConf = HostapdConf('/etc/hostapd/hostapd.conf')
    #ha.set_ssid(APConf, AP.ssid)
    #ha.set_iface(APConf, AP.interface)
    #APConf.write()
    config = AppConfig()
    config.open_file()
    Port = config.ConfigSectionMap("server_port")['port']
    WSPort = config.ConfigSectionMap("server_port")['ws_port']
    print Port
    #linktools = ap_link_tools()
    #devtools = dev_link_tools()
    #aptools = hostapd_tools()
    #ap = linktools.scan_ap()
    #S = station()
#    t = Thread(target=S.station_mode_on())
    #station_mode_on()
    ws_app = tornado.web.Application([(r'/ws', WSHandler),])
    ws_app.listen(Port)
    app = tornado.web.Application(handlers, **settings)
    app.listen(WSPort)
    t2 =Thread(target=tornado.ioloop.IOLoop.current().start())
    tornado.ioloop.IOLoop.current().start()
    try:
        t.start()
        t.join()
    except:
        sys.exit()
