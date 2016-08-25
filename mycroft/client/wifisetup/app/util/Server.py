from wpaCLITools import wpaClientTools
from LinkUtils import ScanForAP
from wpaCLITools import wpaClientTools
from mycroft.util.log import getLogger
import ast
import re
import tornado.websocket
import time
import threading

from mycroft.client.wifisetup.app.util.api import WiFiAPI,\
    ApAPI, LinkAPI

from Queue import Queue

clients = []

wpa_cli = wpaClientTools()


ws_q_in = Queue(10)
ws_q_out = Queue(10)
ap_q_in = Queue(10)
wifi_q_in = Queue(10)
wifi_connection_settings = {}

wifi_api = WiFiAPI()
ap_api = ApAPI()
wifi_api = WiFiAPI()
link_api = LinkAPI()


LOGGER = getLogger("WiFiSetupClient")


def send_to_all_clients(msg):
    for client in clients:
        LOGGER.info('Sending ' + msg + ' to browser')
        client.write_message(msg)


class WsProducerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(WsProducerThread, self).__init__()
        self.target = target
        self.name = name
        return

    def run(self):
        while True:
            if not ws_q_out.empty():
                item = ws_q_out.get()
                send_to_all_clients(item)
        return


class WiFiConsumerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(WiFiConsumerThread, self).__init__()
        self.target = target
        self.name = name
        return

    def run(self):
        while True:
            if not wifi_q_in.empty():
                item = wifi_q_in.get()
                self.message_switch(item)
        return

    def is_match(self, regex, text):
        self.pattern = re.compile(regex)
        return self.pattern.search(text) is not None

    def message_switch(self, message):
        if 'scan' in message:
            wifi_api.scan('uap0')
        if 'connect' in message:
            if wifi_api.try_connect() is True:
                ws_q_out.put('success')
            else:
                ws_q_out.put('unableToConnect')

        elif 'ssid' in message:
            wifi_api.set_ssid(message['ssid'])
        elif 'passphrase' in message:
            wifi_api.set_psk(message['passphrase'])
            wifi_q_in.put({'connect': True})
        else:
            pass

    def stop(self):
        self.stop()


class ApConsumerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(ApConsumerThread, self).__init__()
        self.target = target
        self.name = name
        return

    def run(self):
        while True:
            if not ap_q_in.empty():
                item = ap_q_in.get()
                self.message_switch(item)
        return

    def message_switch(self, message):
        if 'ap_mode' in message:
            if message['ap_mode'] is True:
                # link_api.link_up('uap0')
                time.sleep(5)
                ap_api.up()
            elif message['ap_mode'] is False:
                ap_api.down()
                # link_api.link_down('uap0')
        else:
            pass


class WsConsumerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(WsConsumerThread, self).__init__()
        self.target = target
        self.name = name
        return

    def run(self):
        while True:
            if not ws_q_in.empty():
                item = ws_q_in.get()
                LOGGER.info('recieved ' + item + ' from browser')
                self.message_switch(item)
        return

    def is_match(self, regex, text):
        self.pattern = re.compile(regex)
        return self.pattern.search(text) is not None

    def message_switch(self, message):
        self.dict2 = ast.literal_eval(message)
        if self.is_match("'ap_on'", message) is True:
            ws_q_out.put('TURN AP ON')
            ap_q_in.put({'ap_mode': True})
            # ap_api.up()
        elif self.is_match("'ap_off'", message) is True:
            ws_q_out.put('TURN AP OFF')
            ap_q_in.put({'ap_mode': False})
        elif self.is_match("'scan_networks'", message) is True:
            ws_q_out.put('SCAN NETWORKS')
            wifi_q_in.put({'wifi': 'scan'})
        elif self.is_match("'ssid'", message) is True:
            ws_q_out.put('SSID RECEIVED')
            wifi_q_in.put({'ssid': self.dict2['ssid']})
        elif self.is_match("'passphrase'", message) is True:
            ws_q_out.put('PASSPHRASE RECEIVED')
            wifi_q_in.put({'passphrase': self.dict2['passphrase']})


a = ApConsumerThread('ap')
a.start()

ap_q_in.put({'ap_mode': True})

p = WsProducerThread('producer')
p.start()
c = WsConsumerThread('consumer')
c.start()
w = WiFiConsumerThread('wifi')
w.start()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.client_iface = 'uap0'
        apScan = ScanForAP('scan', self.client_iface)
        apScan.start()
        apScan.join()
        self.ap = apScan.join()
        wifi_q_in.put({'scan': True})
        # wifi = wpaClientTools()
        # self.ap = wifi.wpa_cli_scan(self.client_iface).split()
        # print self.ap
        self.render("index.html", ap=self.ap)


class JSHandler(tornado.web.RequestHandler):
    def get(self):
        LOGGER.info("request for jquery.min.js")
        self.render("jquery-2.2.3.min.js")


class BootstrapMinJSHandler(tornado.web.RequestHandler):
    def get(self):
        LOGGER.info("request for bootstrap,min.js")
        self.render("bootstrap-3.3.7-dist/js/bootstrap.min.js")


class BootstrapMinCSSHandler(tornado.web.RequestHandler):
    def get(self):
        LOGGER.info("request for bootstrap.min.css")
        self.render("bootstrap-3.3.7-dist/css/bootstrap.min.css")


class WSHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        LOGGER.info('a user is connected')
        clients.append(self)

    def on_message(self, message):
        ws_q_in.put(message)

    def on_close(self):
        LOGGER.info('connection closed\n')
        clients.remove(self)
