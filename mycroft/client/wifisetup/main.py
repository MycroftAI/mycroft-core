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
from subprocess import Popen, PIPE
from time import sleep

from pyric import pyw
from wifi import Cell

from mycroft.client.enclosure.api import EnclosureAPI
from mycroft.client.wifisetup.wifi_util import *
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import str2bool
from mycroft.util.log import getLogger

__author__ = 'aatchison'

LOG = getLogger("WiFiClient")


def cli(*args):
    LOG.info("Command: %s" % list(args))
    proc = Popen(args=args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    result = {'code': proc.returncode, 'stdout': stdout, 'stderr': stderr}
    LOG.info("Command result: %s" % result)
    return result


def wpa(*args):
    idx = 0
    result = cli('wpa_cli', *args)
    out = result.get("stdout", "\n")
    if "interface" in out:
        idx = 1
    return str(out.split("\n")[idx])


def sysctrl(*args):
    return cli('systemctl', *args)


class AccessPoint:
    def __init__(self):
        self.iface = 'p2p-wlan0-0'
        self.ip = '172.24.1.1'
        self.ip_start = '172.24.1.50'
        self.ip_end = '172.24.1.150'
        self.password = None

    def up(self):
        try:
            card = pyw.getcard(self.iface)
        except:
            wpa('p2p_group_add', 'persistent=0')
            self.password = wpa('p2p_get_passphrase')
            self.iface = self.get_iface()
            card = pyw.getcard(self.iface)
        pyw.inetset(card, self.ip)

        LOG.info(write_dnsmasq(
            self.iface, self.ip, self.ip_start, self.ip_end
        ))
        sysctrl('restart', 'dnsmasq.service')

    def get_iface(self):
        for iface in pyw.winterfaces():
            if "p2p" in iface:
                return iface

    def down(self):
        sysctrl('stop', 'dnsmasq.service')
        sysctrl('disable', 'dnsmasq.service')
        wpa('p2p_group_remove', self.iface)
        LOG.info(restore_system_files())


class WiFi:
    def __init__(self):
        self.ap = AccessPoint()
        self.client = WebsocketClient()
        self.enclosure = EnclosureAPI(self.client)
        self.config = ConfigurationManager.get().get('WiFiClient')
        self.init_events()
        self.first_setup()

    def init_events(self):
        self.client.on('mycroft.wifi.start', self.start)
        self.client.on('mycroft.wifi.stop', self.stop)
        self.client.on('mycroft.wifi.scan', self.scan)
        self.client.on('mycroft.wifi.connect', self.connect)

    def first_setup(self):
        if str2bool(self.config.get('setup')):
            self.start()
            ConfigurationManager.set('WiFiClient', 'must_start', False)

    def start(self, event=None):
        LOG.info("Starting access point...")
        self.client.emit(Message("speak", metadata={
            'utterance': "Initializing wireless setup mode."}))
        self.ap.up()
        self.iface = self.get_iface()
        self.enclosure.mouth_text(self.ap.password)
        LOG.info("Access point started!\n%s" % self.ap.__dict__)

    def get_iface(self):
        for iface in pyw.winterfaces():
            if iface != self.ap.iface:
                return iface

    def scan(self, event=None):
        LOG.info("Scanning wifi connections...")
        networks = {}

        for cell in Cell.all(self.iface):
            update = True
            quality = self.get_quality(cell.quality)
            if networks.__contains__(cell.ssid):
                update = networks.get(cell.ssid).get("quality") < quality
            if update and cell.ssid:
                networks[cell.ssid] = {
                    'quality': quality,
                    'encrypted': cell.encrypted
                }
        self.client.emit(Message("mycroft.wifi.scanned",
                                 {'networks': networks}))
        LOG.info("Wifi connections scanned!\n%s" % networks)

    @staticmethod
    def get_quality(quality):
        values = quality.split("/")
        return float(values[0]) / float(values[1])

    def connect(self, event=None):
        if event and event.metadata:
            iface = self.get_iface()
            ssid = '"' + event.metadata.get("ssid") + '"'
            LOG.info("Connecting to: %s" % ssid)

            net_id = wpa('-i', iface, 'add_network')
            wpa('-i', iface, 'set_network', net_id, 'ssid', ssid)
            if event.metadata.__contains__("pass"):
                passkey = '"' + event.metadata.get("pass") + '"'
                wpa('-i', iface, 'set_network', net_id, 'psk', passkey)
            else:
                wpa('-i', iface, 'set_network', net_id, 'key_mgmt', 'NONE')
            wpa('-i', iface, 'enable', net_id)
            wpa('save_config')

            connected = self.get_connected()
            self.client.emit(Message("mycroft.wifi.connected",
                                     {'connected': connected}))
            LOG.info("Connection status for %s = %s" % (ssid, connected))

    def get_connected(self):
        retry = 10
        connected = self.is_connected()
        while not connected and retry > 0:
            connected = self.is_connected()
            retry -= 1
            sleep(1)
        return connected

    def is_connected(self):
        res = cli('wpa_cli', '-i', self.iface, 'status', '|', 'grep', 'state')
        return "COMPLETED" in str(res.get("stdout"))

    def stop(self, event=None):
        LOG.info("Stopping access point...")
        self.ap.down()
        LOG.info("Access point stopped!")

    def run(self):
        try:
            self.client.run_forever()
        except Exception as e:
            LOG.error("Error: {0}".format(e))
            self.stop()


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
