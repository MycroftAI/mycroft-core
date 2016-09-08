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


def cli(command):
    result = None
    try:
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if stdout:
            result = {'code': proc.returncode, 'stdout': stdout}
        if stderr:
            result = {'code': proc.returncode, 'stderr': stderr}
    except Exception as e:
        LOG.error("Error: {0}".format(e))
    LOG.error(result)
    return result


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
            cli(['wpa_cli', 'p2p_set', 'ssid_postfix', '_MYCROFT'])
            cli(['wpa_cli', 'p2p_group_add'])
            self.password = self.get_password()
            self.iface = self.get_iface()
            card = pyw.getcard(self.iface)
        pyw.inetset(card, self.ip)

        LOG.info(write_dnsmasq(
            self.iface, self.ip, self.ip_start, self.ip_end
        ))
        cli(['systemctl', 'restart', 'dnsmasq.service'])

    def get_password(self):
        result = cli(['wpa_cli', 'p2p_get_passphrase'])
        return str(result.get("stdout", "").split("\n")[0])

    def get_iface(self):
        for iface in pyw.winterfaces():
            if "p2p" in iface:
                return iface

    def down(self):
        cli(['systemctl', 'stop', 'dnsmasq.service'])
        cli(['systemctl', 'disable', 'dnsmasq.service'])
        cli(['wpa_cli', 'p2p_group_remove', self.iface])
        LOG.info(restore_system_files())


class WiFi:
    def __init__(self):
        self.ap = AccessPoint()
        self.client = WebsocketClient()
        self.enclosure = EnclosureAPI(self.client)
        self.config = ConfigurationManager.get().get('WiFiClient')
        self.client.on('mycroft.wifi.start', self.start)
        self.client.on('mycroft.wifi.stop', self.stop)
        self.client.on('mycroft.wifi.scan', self.scan)
        self.client.on('mycroft.wifi.connect', self.connect)
        self.first_setup()
        self.cells = {}

    def first_setup(self):
        if str2bool(self.config.get('setup')):
            self.start()
            ConfigurationManager.set('WiFiClient', 'must_start', False)

    def start(self, event=None):
        LOG.info("Starting access point...")
        self.client.emit(Message("speak", metadata={
            'utterance': "Initializing wireless setup mode."}))
        self.ap.up()
        self.enclosure.mouth_text(self.ap.password)
        LOG.info("Access point started!")

    def scan(self, event=None):
        LOG.info("Scanning wifi connections...")
        networks = {}
        self.cells = {}
        self.interfaces = pyw.winterfaces()

        for cell in Cell.all(self.interfaces[0]):
            update = True
            quality = self.get_quality(cell.quality)
            if networks.__contains__(cell.ssid):
                update = networks.get(cell.ssid).get("quality") < quality
            if update and cell.ssid:
                self.cells[cell.ssid] = cell
                networks[cell.ssid] = {
                    'quality': quality,
                    'encrypted': cell.encrypted
                }
        self.client.emit(Message("mycroft.wifi.scanned",
                                 {'networks': networks}))
        LOG.info("Wifi connections scanned: %s" % networks)

    @staticmethod
    def get_quality(quality):
        values = quality.split("/")
        return float(values[0]) / float(values[1])

    def connect(self, event=None):
        if event and event.metadata:
            ssid = event.metadata.get("ssid")
            passkey = event.metadata.get("pass")
            LOG.info("Connecting to: %s" % ssid)

            result = cli(['wpa_cli', '-iwlan0', 'add_network'])
            net_id = self.get_result(result)
            cli(['wpa_cli', '-iwlan0', 'set_network', net_id, 'ssid', ssid])
            if passkey:
                cli(['wpa_cli', '-iwlan0', 'set_network', net_id, 'psk', passkey])
            else:
                cli(['wpa_cli', '-iwlan0', 'set_network', net_id, 'key_mgmt', 'NONE'])
            cli(['wpa_cli', '-iwlan0', 'enable', net_id])

            connected = self.get_connected()
            self.client.emit(Message("mycroft.wifi.connected",
                                     {'connected': connected}))
            LOG.info("Wifi connection status to: %s" % ssid)

    def get_connected(self):
        retry = 22
        connected = self.is_connected()
        while not connected:
            connected = self.is_connected()
            retry -= 1
            sleep(1)
        return connected

    def is_connected(self):
        result = cli(['wpa_cli', '-iwlan0', 'status', '|', 'grep', 'state'])
        return self.get_result(result) == "wpa_state=COMPLETED"

    def get_result(self, result):
        return str(result.get("stdout", "").split("\n")[0])


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
