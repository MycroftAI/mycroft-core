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

LOGGER = getLogger("WiFiClient")


def bash_command(command):
    result = None
    try:
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if stdout:
            result = {
                'exit': 0, 'returncode': proc.returncode, 'stdout': stdout}
        if stderr:
            result = {'exit': 0,
                      'returncode': proc.returncode,
                      'stdout': stderr}
    except OSError as e:
        result = {'exit': 1,
                  'os_errno': e.errno,
                  'os_stderr': e.strerror,
                  'os_filename': e.filename}
    except:
        result = {'exit': 2, 'sys': sys.exc_info()[0]}

    return result


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

        LOGGER.info(write_dnsmasq(
            self.iface, self.ip, self.ip_start,
            self.ip_end
        ))
        LOGGER.info(write_hostapd_conf(
            self.iface, 'nl80211', 'mycroft-' + str(uuid.getnode()), str(6)
        ))
        LOGGER.info(write_default_hostapd('/etc/hostapd/hostapd.conf'))
        bash_command(['systemctl', 'restart', 'dnsmasq.service'])
        bash_command(['systemctl', 'restart', 'hostapd.service'])

    def down(self):
        bash_command(['systemctl', 'stop', 'hostapd.service'])
        bash_command(['systemctl', 'stop', 'dnsmasq.service'])
        bash_command(['systemctl', 'disable', 'hostapd.service'])
        bash_command(['systemctl', 'disable', 'dnsmasq.service'])
        LOGGER.info(restore_system_files())


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
        self.client.emit(Message("speak", metadata={
            'utterance': "Initializing wireless setup mode."}))
        self.ap.up()

    def scan(self, event=None):
        networks = {}
        self.cells = {}
        interface = pyw.winterfaces()[0]

        for cell in Cell.all(interface):
            update = True
            if networks.__contains__(cell.ssid):
                update = networks.get(cell.ssid).get("quality") < cell.quality
            if update and cell.ssid:
                self.cells[cell.sid] = cell
                networks[cell.ssid] = {
                    'quality': cell.quality,
                    'encrypted': cell.encrypted
                }
        self.client.emit(Message("mycroft.wifi.networks",
                                 {'networks': networks}))

    def connect(self, event=None):
        if event and event.metadata:
            try:
                ssid = event.metadata.get("ssid")
                passkey = event.metadata.get("pass")
                cell = self.cells[ssid]
                scheme = Scheme.for_cell(self.ap.iface, ssid, cell, passkey)
                scheme.activate()
                scheme.save()
                self.client.emit(Message("mycroft.wifi.connected",
                                         {'connected': True}))
            except Exception as e:
                LOGGER.error("Wifi Client error: {0}".format(e))
                self.client.emit(Message("mycroft.wifi.connected",
                                         {'connected': False}))

    def stop(self, event=None):
        self.ap.down()
        # TODO - STOP EVERYTHING!!!!
        pass

    def run(self):
        try:
            self.client.run_forever()
        except Exception as e:
            LOGGER.error("Wifi Client error: {0}".format(e))
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
