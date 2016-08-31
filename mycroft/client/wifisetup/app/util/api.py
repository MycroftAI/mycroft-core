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
import sys
import threading
from operator import itemgetter
from collections import defaultdict
from wifi import Cell
from pyroute2 import IPRoute
from uuid import getnode as get_mac

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
        network_id = self.wpa_tools.wpa_cli_add_network(
            self.client_iface)['stdout']
        if self.passphrase != '':
            LOGGER.info(self.wpa_tools.wpa_cli_set_network(
                self.client_iface, network_id, 'ssid', self.ssid))
            LOGGER.info(self.wpa_tools.wpa_cli_set_network(
                self.client_iface, network_id, 'psk', self.passphrase))
            LOGGER.info(
                self.wpa_tools.wpa_cli_enable_network(
                    self.client_iface, network_id))
        elif self.passphrase == 'None':
            LOGGER.info(self.wpa_tools.wpa_cli_set_network(
                self.client_iface, network_id, 'ssid', self.ssid))
            LOGGER.info(self.wpa_tools.wpa_cli_set_network(
                self.client_iface, network_id, 'key_mgmt', 'NONE'))
            LOGGER.info(
                self.wpa_tools.wpa_cli_enable_network(
                    self.client_iface, network_id))

        connected = False
        while connected is False:
            for i in range(22):
                time.sleep(1)
                try:
                    state = self.wpa_tools.wpa_cli_status(
                        self.client_iface)['wpa_state']
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
        self.wpa_tools.wpa_cli_set_network(
            self.client_iface, str(self.new_net), '', psk)

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
        self.ap_iface_ip_range_start = \
            self.config.get('ap_iface_ip_range_start')
        self.ap_iface_ip_range_end = \
            self.config.get('ap_iface_ip_range_stop')
        self.ap_iface_mac = self.config.get('ap_iface_mac')

    def up(self):
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
        LOGGER.info(bash_command(['systemctl', 'stop', 'dnsmasq.service']))
        LOGGER.info(bash_command(['systemctl', 'start', 'dnsmasq.service']))
        LOGGER.info(bash_command(['systemctl', 'stop', 'hostapd.service']))
        LOGGER.info(bash_command(['systemctl', 'start', 'hostapd.service']))
        LOGGER.info(bash_command(['ifup', self.client_iface]))

    def down(self):
        LOGGER.info(self.ap_tools.hostAPDStop())
        LOGGER.info(self.dns_tools.dnsmasqServiceStop())
        LOGGER.info(restore_system_files())
        LOGGER.info(bash_command(['ifdown', self.ap_iface]))
        LOGGER.info(bash_command(['ifdown', self.client_iface]))
        LOGGER.info(bash_command(['ifup', self.client_iface]))


class WpaClientTools:
    def __init__(self):
        self.name = "name"

    def wpa_cli_flush(self):
        results = bash_command(['wpa_cli', 'flush'])
        return results

    def wpa_cli_scan(self, iface):
        bash_command(['wpa_cli', '-i', iface, 'scan'])
        results = bash_command(
            ['wpa_cli', 'scan_results'])['stdout'].split('\n')
        for result in results:
            results['network'].append()
        return results

    def wpa_cli_status(self, iface):
        status = bash_command(['wpa_cli', '-i', iface, 'status'])
        status = status['stdout'].split('\n', 13)
        results = {
            "bssid": status[0].split("=", 1)[1],
            "freq": status[1].split("=", 1)[1],
            "ssid": status[2].split("=", 1)[1],
            "id": status[3].split("=", 1)[1],
            "mode": status[4].split("=", 1)[1],
            "pairwise_cipher": status[5].split("=", 1)[1],
            "group_cipher": status[6].split("=", 1)[1],
            "key_mgmt": status[7].split("=", 1)[1],
            "wpa_state": status[8].split("=", 1)[1],
            "ip_address": status[9].split("=", 1)[1],
            "p2p_device_address": status[10].split("=", 1)[1],
            "address": status[11].split("=", 1)[1],
            "uuid": status[12].split("=", 1)[1]
        }
        return results

    def wpa_cli_add_network(self, iface):
        results = bash_command(['wpa_cli', '-i', iface, 'add_network'])
        return results

    def wpa_cli_set_network(self, iface,
                            network_id, network_var, network_var_value):
        results = bash_command(['wpa_cli',
                                '-i', iface,
                                'set_network',
                                network_id,
                                network_var,
                                network_var_value])
        return results

    def wpa_cli_enable_network(self, iface, network_id):
        results = bash_command(['wpa_cli', '-i', iface, 'enable', network_id])
        return results

    def wpa_cli_disable_network(self, iface, network_id):
        results = bash_command(['wpa_cli', '-i', iface, 'disable', network_id])
        return results

    def wpa_save_network(self, network_id):
        results = bash_command(['wpa_cli', 'save', network_id])
        return results


class ScanForAP(threading.Thread):
    def __init__(self, name, interface):
        threading.Thread.__init__(self)
        self.name = name
        self.interface = interface
        self._return = []
        print sys.modules['os']

    def run(self):
        ap_scan_results = defaultdict(list)
        try:
            for cell in Cell.all(self.interface):
                ap_scan_results['network'].append({
                    'ssid': cell.ssid,
                    'signal': cell.signal,
                    'quality': cell.quality,
                    'frequency': cell.frequency,
                    'encrypted': cell.encrypted,
                    'channel': cell.channel,
                    'address': cell.address,
                    'mode': cell.mode
                })
            nets_byNameAndStr = sorted(ap_scan_results['network'],
                                       key=itemgetter('ssid', 'quality'),
                                       reverse=True)
            lastSSID = "."
            for n in nets_byNameAndStr[:]:
                if (n['ssid'] == lastSSID):
                    nets_byNameAndStr.remove(n)
                else:
                    lastSSID = n['ssid']
            ap_scan_results['network'] = sorted(
                nets_byNameAndStr, key=itemgetter('quality'), reverse=True)
            self._return = ap_scan_results
        except:
            print "ap scan fail"

    def join(self):
        threading.Thread.join(self)
        return self._return


class APLinkTools:
    def __init__(self):
        self.config = ConfigurationManager.get().get('WiFiClient')
        self.client_iface = self.config.get('client_iface')
        pass

    def connect_to_wifi(self, ssid, passphrase):
        print " connecting to wifi:", ssid, passphrase
        self.template = """country={country}
    ctrl_interface=/var/run/wpa_supplicant
    update_config=1
    network={b1}
        ssid="{ssid}"
        psk="{passphrase}"
        key_mgmt=WPA-PSK
    {b2}"""
        self.context = {
            "b1": '{',
            "b2": '}',
            "country": 'US',
            "ssid": ssid,
            "passphrase": passphrase
        }
        with open(
                '/etc/wpa_supplicant/wpa_supplicant.conf', 'w'
        ) as self.myfile:
            self.myfile.write(self.template.format(**self.context))
            self.myfile.close()
        try:
            print bash_command(['ip', 'addr', 'flush', self.client_iface])
            print bash_command(['ifdown', self.client_iface])
            print bash_command(['ifup', self.client_iface])
        except:
            print "connection failed"
            print bash_command(['ip', 'addr', 'flush', self.client_iface])
