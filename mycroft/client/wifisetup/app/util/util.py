#!/usr/bin/env python
import threading
import sys
import httplib
from pyroute2 import IPRoute
from operator import itemgetter
from collections import defaultdict
from wifi import Cell
from mycroft.client.wifisetup.app.util.BashThreadHandling import bash_command
from mycroft.util.log import getLogger

ip = IPRoute()
LOGGER = getLogger("WiFiSetupClient")


class DnsmasqTools:
    def __init__(self):
        self.name = "name"

    def dnsmasqServiceStart(self):
        results = bash_command(['systemctl', 'start', 'dnsmasq.service'])
        return results

    def dnsmasqServiceStop(self):
        results = bash_command(['systemctl', 'stop', 'dnsmasq.service'])
        return results

    def dnsmasqServiceStatus(self):
        results = bash_command(['systemctl', 'status', 'dnsmasq.service'])
        return results

    def dnsmasqCli(self):
        results = bash_command(['dnsmasq', '-d',
                                '--interface=uap0',
                                '--dhcp-range=uap0,'
                                '172.24.1.10,'
                                '172.24.1.20,'
                                '255.255.255.0'])
        return results


class HostAPServerTools:
    def __init__(self):
        self.name = "name"

    def hostAPDStart(self):
        results = bash_command(['systemctl', 'start', 'hostapd.service'])
        return results

    def hostAPDStop(self):
        results = bash_command(['systemctl', 'stop', 'hostapd.service'])
        return results

    def hostAPDStatus(self):
        results = bash_command(['systemctl', 'status', 'hostapd.service'])
        return results

    def hostAPDCli(self):
        results = bash_command(['hostapd', '/etc/hostapd/hostapd.conf'])
        return results


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

    def wpa_cli_loglevel_debug(self, iface):
        results = bash_command(['wpa_cli', '-i', iface, 'log_level', 'debug'])
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
            #################################################
            # Clean up the list of networks.
            #################################################
            # First, sort by name and strength
            nets_byNameAndStr = sorted(ap_scan_results['network'],
                                       key=itemgetter('ssid', 'quality'),
                                       reverse=True)
            # now strip out duplicates (e.g. repeaters with the same SSID),
            # keeping the first (strongest)
            lastSSID = "."
            for n in nets_byNameAndStr[:]:
                if (n['ssid'] == lastSSID):
                    nets_byNameAndStr.remove(n)
                else:
                    lastSSID = n['ssid']
                    # Finally, sort by strength alone
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
        pass

    def scan_links(self):
        return [x.get_attr('IFLA_IFNAME') for x in ip.get_links()]

    def internet_on(host="127.0.0.1", port=80, timeout=3):
        conn = httplib.HTTPConnection("www.google.com")
        try:
            conn.request("HEAD", "/")
            return True
        except:
            return False

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
            print bash_command(["ip addr flush wlan0"])
            print bash_command(["ifdown wlan0"])
            print bash_command(["ifup wlan0"])
        except:
            print "connection failed"


class HostAPDTools:
    def ap_config(self):
        bash_command(
            'bash -x /home/pi/rpi3-headless-wifi-setup/'
            'hostapd-shell/config-change-ap-on.sh')

    def ap_deconfig(self):
        bash_command(
            'bash -x  /home/pi/rpi3-headless-wifi-setup/'
            'hostapd-shell/config-change-restore.sh')

    def ap_up(self):
        bash_command(
            'bash -x /home/pi/rpi3-headless-wifi-setup/'
            'hostapd-shell/ap-up.sh')

    def ap_down(self):
        bash_command(
            'bash -x /home/pi/rpi3-headless-wifi-setup/'
            'hostapd-shell/ap-down.sh')

    def dnsmasq_start(self):
        bash_command(["systemctl", "start", "dnsmasq.service"])

    def dnsmasq_stop(self):
        bash_command(["systemctl", "stop", "dnsmasq.service"])

    def hostapd_start(self):
        print bash_command(["systemctl", "start", "hostapd.service"])

    def hostapd_stop(self):
        print bash_command(['systemctl', 'stop', 'hostapd.service'])
