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
import uuid

from pyric import pyw
from wifi import Cell
from wifi.scheme import Scheme

from mycroft.client.wifisetup.wifi_util import *
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import str2bool
from mycroft.util.log import getLogger

__author__ = 'aatchison'

LOG = getLogger("WiFiClient")


def bash_command(command):
    try:
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if stdout:
            LOG.info({'code': proc.returncode, 'stdout': stdout})
        if stderr:
            LOG.info({'code': proc.returncode, 'stderr': stderr})
    except Exception as e:
        LOG.error("Error: {0}".format(e))


class AccessPoint:
    def __init__(self):
        self.iface = 'uap0'
        self.ip = '172.24.1.1'
        self.ip_start = '172.24.1.10'
        self.ip_end = '172.24.1.20'

    def up(self):
        try:
            ap = pyw.getcard(self.iface)
        except:
            interface = pyw.winterfaces()[0]
            card = pyw.getcard(interface)
            pyw.pwrsaveset(card, False)
            ap = pyw.phyadd(card, self.iface, 'AP')
        pyw.inetset(ap, self.ip)

        LOG.info(write_dnsmasq(
            self.iface, self.ip, self.ip_start,
            self.ip_end
        ))
        LOG.info(write_hostapd_conf(
            self.iface, 'nl80211', 'mycroft-' + str(uuid.getnode()), str(6)
        ))
        LOG.info(write_default_hostapd('/etc/hostapd/hostapd.conf'))
        bash_command(['systemctl', 'restart', 'dnsmasq.service'])
        bash_command(['systemctl', 'restart', 'hostapd.service'])

    def down(self):
        bash_command(['systemctl', 'stop', 'hostapd.service'])
        bash_command(['systemctl', 'stop', 'dnsmasq.service'])
        bash_command(['systemctl', 'disable', 'hostapd.service'])
        bash_command(['systemctl', 'disable', 'dnsmasq.service'])
        LOG.info(restore_system_files())


class WiFi:
    def __init__(self):
        self.ap = AccessPoint()
        self.client = WebsocketClient()
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
            try:
                cell = self.cells[ssid]
                interface = self.interfaces[1]
                scheme = Scheme.for_cell(interface, ssid, cell, passkey)
                scheme.save()
                scheme.activate()
                self.client.emit(Message("mycroft.wifi.connected",
                                         {'connected': True}))
                LOG.info("Wifi connected to: %s" % ssid)
            except Exception as e:
                LOG.warn("Unable to connect to: %s" % ssid)
                LOG.error("Error: {0}".format(e))
                self.client.emit(Message("mycroft.wifi.connected",
                                         {'connected': False}))

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
