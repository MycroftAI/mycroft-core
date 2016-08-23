from wpaCLITools import wpaClientTools
from LinkUtils import ScanForAP
from wpaCLITools import wpaClientTools
from mycroft.util.log import getLogger
import ast
import re
import tornado.websocket
import time
import threading

from Queue import Queue

clients = []

ws_q_in = Queue(10)
ws_q_out = Queue(10)

ap_q_in = Queue(10)

wifi_q_in = Queue(10)

wifi_connection_settings = {}

LOGGER = getLogger("WiFiSetupClient")

def send_to_all_clients(msg):
    for client in clients:
        LOGGER.info('Sending ' + msg + ' to browser')
        client.write_message(msg)


class WsProducerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
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
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
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
            print 'Scan goes here'
        if 'connect' in message:
            print 'Connect goes here'
        elif 'ssid' in message:
            print message['ssid']
            wifi_connection_settings['ssid'] = message['ssid']
            print wifi_connection_settings
        elif 'passphrase' in message:
            print message['passphrase']
            wifi_connection_settings['passphrase'] = message['passphrase']
            wifi_q_in.put({'connect': True})
        else:
            pass

class ApConsumerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
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
                print 'AP mode on Here'
            elif message['ap_mode'] is False:
                print 'AP mode off here'
        else:
            pass

class WsConsumerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
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
            #wifi_connection_settings['passphrase'] = self.dict2['passphrase']
            #ssid = wifi_connection_settings['ssid']
            #passphrase = self.dict2['passphrase']
            #ssid = '''"''' + ssid + '''"'''
            #passphrase = '''"''' + passphrase + '''"'''
            #WiFi = wpaClientTools()
            #network_id = WiFi.wpa_cli_add_network(
            #    self.client_iface)['stdout'].strip()
            #LOGGER.info(network_id)
            #LOGGER.info(WiFi.wpa_cli_set_network(
            #    self.client_iface, str(network_id), 'ssid', ssid))
            #LOGGER.info(WiFi.wpa_cli_set_network(
            #    self.client_iface, str(network_id), 'psk', passphrase))
            #LOGGER.info(WiFi.wpa_cli_enable_network(
            #    self.client_iface, network_id))
            #x = 15
            #while x > 0:
            #    try:
            #        if WiFi.wpa_cli_status(
            #                self.client_iface)['wpa_state'] == 'COMPLETED':
            #            LOGGER.info("CONNECTED")
            #            self.write_message("Authenication Sucessful")
            #            LOGGER.info(
            #                WiFi.wpa_save_network(str(network_id)))
            #            self.write_message(
            #                "Saving Network SSID and Passphrase")
            #            LOGGER.info(
            #                WiFi.wpa_cli_disable_network(str(network_id)))
            #            x = 0
            #    except:
            #        self.write_message("Attempting to Authenticate")
            #        LOGGER.info("Attemping to Authenticate")
            #        x -= 1
            #        time.sleep(1)



p = WsProducerThread('producer')
p.start()
c = WsConsumerThread('consumer')
c.start()
w = WiFiConsumerThread('wifi')
w.start()
a = ApConsumerThread('ap')
a.start()


class APConfig():
    def __init__(self):
        file_template = 'config.templates/etc/hostapd/hostapd.conf.template'
        file_path = '/etc/hostapd/hostapd.conf'
        interface = 'wlan0'
        driver = 'nl80211'
        ssid = 'PI3-AP'
        hw_mode = 'g'
        channel = 6
        country_code = 'US'
        ieee80211n = 1
        wmm_enabled = 1
        ht_capab = '[HT40][SHORT-GI-20][DSSS_CCK-40]'
        macaddr_acl = 0
        ignore_broadcast_ssid = 0

    def write_config(self):
        ha.set_ssid(APConf, self.ssid)
        APConf.write()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.client_iface = 'wlp3s0'
        apScan = ScanForAP('scan', self.client_iface)
        apScan.start()
        apScan.join()
        self.ap = apScan.join()
        #wifi = wpaClientTools()
        #self.ap = wifi.wpa_cli_scan(self.client_iface).split()
        #print self.ap
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

