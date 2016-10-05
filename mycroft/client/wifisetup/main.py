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
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import TCPServer
from shutil import copyfile
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep

import os
from os.path import join, dirname, realpath
from pyric import pyw
from wifi import Cell

from mycroft.client.enclosure.api import EnclosureAPI
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
    result = cli('wpa_cli', '-i', *args)
    out = result.get("stdout", "\n")
    if "interface" in out:
        idx = 1
    return str(out.split("\n")[idx])


def sysctrl(*args):
    return cli('systemctl', *args)


class WebServer(Thread):
    DIR = dirname(realpath(__file__))

    def __init__(self, host, port):
        super(WebServer, self).__init__()
        self.daemon = True
        self.server = TCPServer((host, port), SimpleHTTPRequestHandler)

    def run(self):
        LOG.info("Starting Web Server at %s:%s" % self.server.server_address)
        os.chdir(join(self.DIR, 'web'))
        self.server.serve_forever()
        LOG.info("Web Server stopped!")


class AccessPoint:
    template = """interface={interface}
bind-interfaces
server={server}
domain-needed
bogus-priv
dhcp-range={dhcp_range_start}, {dhcp_range_end}, 12h
address=/#/{server}
"""

    def __init__(self, wiface):
        self.wiface = wiface
        self.iface = 'p2p-wlan0-0'
        self.ip = '172.24.1.1'
        self.ip_start = '172.24.1.50'
        self.ip_end = '172.24.1.150'
        self.password = None

    def up(self):
        try:
            card = pyw.getcard(self.iface)
        except:
            wpa(self.wiface, 'p2p_group_add', 'persistent=0')
            self.iface = self.get_iface()
            self.password = wpa(self.iface, 'p2p_get_passphrase')
            card = pyw.getcard(self.iface)
        pyw.inetset(card, self.ip)
        copyfile('/etc/dnsmasq.conf', '/tmp/dnsmasq-bk.conf')
        self.save()
        sysctrl('restart', 'dnsmasq.service')

    def get_iface(self):
        for iface in pyw.winterfaces():
            if "p2p" in iface:
                return iface

    def down(self):
        sysctrl('stop', 'dnsmasq.service')
        sysctrl('disable', 'dnsmasq.service')
        wpa(self.wiface, 'p2p_group_remove', self.iface)
        copyfile('/tmp/dnsmasq-bk.conf', '/etc/dnsmasq.conf')

    def save(self):
        data = {
            "interface": self.iface,
            "server": self.ip,
            "dhcp_range_start": self.ip_start,
            "dhcp_range_end": self.ip_end
        }
        try:
            LOG.info("Writing to: /etc/dnsmasq.conf")
            with open('/etc/dnsmasq.conf', 'w') as f:
                f.write(self.template.format(**data))
        except Exception as e:
            LOG.error("Fail to write: /etc/dnsmasq.conf")
            raise e


class WiFi:
    NAME = "WiFiClient"

    def __init__(self):
        self.iface = pyw.winterfaces()[0]
        self.ap = AccessPoint(self.iface)
        self.server = None
        self.client = WebsocketClient()
        self.enclosure = EnclosureAPI(self.client)
        self.config = ConfigurationManager.get().get(self.NAME)
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

    def start(self, event=None):
        LOG.info("Starting access point...")
        self.client.emit(Message("speak", metadata={
            'utterance': "Initializing wireless setup mode."}))
        self.ap.up()
        if not self.server:
            self.server = WebServer(self.ap.ip, 80)
            self.server.start()
        self.enclosure.mouth_text(self.ap.password)
        LOG.info("Access point started!\n%s" % self.ap.__dict__)

    def scan(self, event=None):
        LOG.info("Scanning wifi connections...")
        networks = {}
        status = self.get_status()

        for cell in Cell.all(self.iface):
            update = True
            ssid = cell.ssid
            quality = self.get_quality(cell.quality)

            if networks.__contains__(ssid):
                update = networks.get(ssid).get("quality") < quality
            if update and ssid:
                networks[ssid] = {
                    'quality': quality,
                    'encrypted': cell.encrypted,
                    'connected': self.is_connected(ssid, status)
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
            ssid = event.metadata.get("ssid")
            connected = self.is_connected(ssid)

            if connected:
                LOG.warn("Mycroft is already connected to %s" % ssid)
            else:
                self.disconnect()
                LOG.info("Connecting to: %s" % ssid)
                nid = wpa(self.iface, 'add_network')
                wpa(self.iface, 'set_network', nid, 'ssid', '"' + ssid + '"')

                if event.metadata.__contains__("pass"):
                    psk = '"' + event.metadata.get("pass") + '"'
                    wpa(self.iface, 'set_network', nid, 'psk', psk)
                else:
                    wpa(self.iface, 'set_network', nid, 'key_mgmt', 'NONE')

                wpa(self.iface, 'enable', nid)
                connected = self.get_connected(ssid)
                if connected:
                    wpa(self.iface, 'save_config')
                    # ConfigurationManager.set(self.NAME, 'setup', False, True)

            self.client.emit(Message("mycroft.wifi.connected",
                                     {'connected': connected}))
            LOG.info("Connection status for %s = %s" % (ssid, connected))

    def disconnect(self):
        status = self.get_status()
        nid = status.get("id")
        if nid:
            ssid = status.get("ssid")
            wpa(self.iface, 'disable', nid)
            LOG.info("Disconnecting %s id: %s" % (ssid, nid))

    def get_status(self):
        res = cli('wpa_cli', '-i', self.iface, 'status')
        out = str(res.get("stdout"))
        if out:
            return dict(o.split("=") for o in out.split("\n")[:-1])
        return {}

    def get_connected(self, ssid, retry=5):
        connected = self.is_connected(ssid)
        while not connected and retry > 0:
            sleep(2)
            retry -= 1
            connected = self.is_connected(ssid)
        return connected

    def is_connected(self, ssid, status=None):
        status = status or self.get_status()
        state = status.get("wpa_state")
        return status.get("ssid") == ssid and state == "COMPLETED"

    def stop(self, event=None):
        LOG.info("Stopping access point...")
        self.ap.down()
        if self.server:
            self.server.server.shutdown()
            self.server.server.server_close()
            self.server.join()
            self.server = None
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
