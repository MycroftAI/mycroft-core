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

import time
from pyroute2 import IPRoute
from uuid import getnode as get_mac
from mycroft.client.wifisetup.app.util.util import HostAPServerTools,\
    DnsmasqTools, WpaClientTools
from mycroft.client.wifisetup.app.util.FileUtils import write_dnsmasq,\
    write_hostapd_conf, write_wpa_supplicant_conf, write_network_interfaces,\
    backup_system_files, restore_system_files, write_default_hostapd
from mycroft.client.wifisetup.app.util.BashThreadHandling import bash_command
from mycroft.util.log import getLogger
from mycroft.configuration import ConfigurationManager


ip = IPRoute()

LOGGER = getLogger("WiFiSetupClient")


class WiFiAPI:
    def __init__(self):
        self.none = None
        self.config = ConfigurationManager.get().get('WiFiClient')
        self.client_iface = self.config.get('client_iface')
        self.wpa_tools = WpaClientTools()
        self.ssid = None
        self.passphrase = ''

    def scan(self, iface):
        self.new_net = self.wpa_tools.wpa_cli_add_network(self.client_iface)

    def try_connect(self):
        self.ssid = '"' + self.ssid + '"'
        self.passphrase = '"' + self.passphrase + '"'
        network_id = self.wpa_tools.wpa_cli_add_network(self.client_iface)['stdout']
        if self.passphrase != '':
            LOGGER.info(self.wpa_tools.wpa_cli_set_network(
                self.client_iface, network_id, 'ssid', self.ssid))
            LOGGER.info(self.wpa_tools.wpa_cli_set_network(
                self.client_iface, network_id, 'psk', self.passphrase))
            LOGGER.info(
                self.wpa_tools.wpa_cli_enable_network(self.client_iface, network_id))
        elif self.passphrase == '':
            LOGGER.info(self.wpa_tools.wpa_cli_set_network(
                self.client_iface, network_id, 'ssid', self.ssid))
            LOGGER.info(self.wpa_tools.wpa_cli_set_network(
                self.client_iface, network_id, 'key_mgmt', 'NONE'))
            LOGGER.info(
                self.wpa_tools.wpa_cli_enable_network(self.client_iface, network_id))

        connected = False
        while connected is False:
            for i in range(22):
                time.sleep(1)
                try:
                    state = self.wpa_tools.wpa_cli_status(self.client_iface)['wpa_state']
                    if state == 'COMPLETED':
                        self.save_wpa_network(self.ssid, self.passphrase)
                        connected = True
                        return True
                    else:
                        connected = False
                except:
                    LOGGER.info("Connection attempt in progress")
                    pass
            if connected is False:
                return False

    def set_ssid(self, ssid):
        self.ssid = ssid
        self.wpa_tools.wpa_cli_set_network(
            self.client_iface, str(self.new_net), 'ssid', ssid)

    def set_psk(self, psk):
        self.passphrase = psk
        self.wpa_tools.wpa_cli_set_network(self.client_iface, str(self.new_net), '', psk)

    def save_wpa_network(self, ssid, passphrase):
        LOGGER.info(write_wpa_supplicant_conf(ssid, passphrase))


class LinkAPI():
    def __init__(self):
        self.none = None

    def link_up(self, iface):
        LOGGER.info(bash_command(['ifup', iface]))

    def link_down(self, iface):
        LOGGER.info(bash_command(['ifdown', iface]))

    def create_vap(self, iface, vap_id):
        LOGGER.info(bash_command(
            'iw', 'dev', iface, 'interface', 'add', vap_id, 'type __ap'))


class ApAPI():
    def __init__(self):
        self.none = None
        self.config = ConfigurationManager.get().get('WiFiClient')
        self.client_iface = self.config.get('client_iface')
        self.ap_iface = self.config.get('ap_iface')
        self.ap_iface_ip = self.config.get('ap_iface_ip')
        self.ap_iface_ip_range_start = self.config.get('ap_iface_ip_range_start')
        self.ap_iface_ip_range_end = self.config.get('ap_iface_ip_range_stop')
        self.ap_iface_mac = self.config.get('ap_iface_mac')

        self.ap_tools = HostAPServerTools()
        self.dns_tools = DnsmasqTools()

    def up(self):
        # LOGGER.info(bash_command(['service', 'dhcpcd', 'stop']))
        LOGGER.info(bash_command(
            ['iw', self.client_iface, 'set', 'power_save', 'off'])
        )
        LOGGER.info(backup_system_files())
        LOGGER.info(
            bash_command(
                ['iw', 'dev', self.client_iface, 'interface',
                 'add', self.ap_iface, 'type', '__ap']))
        LOGGER.info(
            write_network_interfaces(
                self.client_iface, self.ap_iface, self.ap_iface_ip,
                self.ap_iface_mac))
        LOGGER.info(
            write_dnsmasq(
                self.ap_iface, self.ap_iface_ip, self.ap_iface_ip_range_start,
                self.ap_iface_ip_range_end))
        LOGGER.info(
            write_hostapd_conf(
                self.ap_iface, 'nl80211', 'mycroft-' + str(get_mac()), str(1)))
        LOGGER.info(
            write_default_hostapd('/etc/hostapd/hostapd.conf'))
        LOGGER.info(bash_command(['ifdown',  self.client_iface]))
        LOGGER.info(bash_command(['ifdown', self.ap_iface]))
        LOGGER.info(bash_command(
            ['ip', 'link', 'set', 'dev', self.ap_iface,
             'address', self.ap_iface_mac]))
        LOGGER.info(bash_command(['ifup', self.ap_iface]))
        time.sleep(2)
        LOGGER.info(self.dns_tools.dnsmasqServiceStop())
        LOGGER.info(self.dns_tools.dnsmasqServiceStart())
        LOGGER.info(self.ap_tools.hostAPDStop())
        LOGGER.info(self.ap_tools.hostAPDStart())
        LOGGER.info(bash_command(['ifup', self.client_iface]))

    def down(self):
        LOGGER.info(self.ap_tools.hostAPDStop())
        LOGGER.info(self.dns_tools.dnsmasqServiceStop())
        LOGGER.info(restore_system_files())
        LOGGER.info(bash_command(['ifdown', self.ap_iface]))
        LOGGER.info(bash_command(['ifdown', self.client_iface]))
        LOGGER.info(bash_command(['ifup', self.client_iface]))
