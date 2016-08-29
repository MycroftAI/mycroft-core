import time
import sys
from pyroute2 import IPRoute

from mycroft.client.wifisetup.app.util.hostAPDTools import hostAPServerTools
from mycroft.client.wifisetup.app.util.dnsmasqTools import dnsmasqTools
from mycroft.client.wifisetup.app.util.FileUtils import write_dnsmasq,\
    write_hostapd_conf, write_wpa_supplicant_conf, write_network_interfaces,\
    backup_system_files, restore_system_files, write_default_hostapd
from mycroft.client.wifisetup.app.util.wpaCLITools import wpaClientTools
from mycroft.client.wifisetup.app.util.bashThreadHandling import bash_command
from mycroft.util.log import getLogger


ip = IPRoute()

LOGGER = getLogger("WiFiSetupClient")


class WiFiAPI:
    def __init__(self):
        self.none = None
        self.wpa_tools = wpaClientTools()
        self.ssid = None
        self.passphrase = None

    def scan(self, iface):
        self.new_net = self.wpa_tools.wpa_cli_add_network('wlan0')

    def try_connect(self):
        self.ssid = '"' + self.ssid + '"'
        self.passphrase = '"' + self.passphrase + '"'
        network_id = self.wpa_tools.wpa_cli_add_network('wlan0')['stdout']
        LOGGER.info(self.wpa_tools.wpa_cli_set_network(
            'wlan0', network_id, 'ssid', self.ssid))
        LOGGER.info(self.wpa_tools.wpa_cli_set_network(
            'wlan0', network_id, 'psk', self.passphrase))
        LOGGER.info(self.wpa_tools.wpa_cli_enable_network('wlan0', network_id))
        connected = False
        while connected is False:
            for i in range(22):
                time.sleep(1)
                try:
                    state = self.wpa_tools.wpa_cli_status('wlan0')['wpa_state']
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
            'wlan0', str(self.new_net), 'ssid', ssid)

    def set_psk(self, psk):
        self.passphrase = psk
        self.wpa_tools.wpa_cli_set_network('wlan0', str(self.new_net), '', psk)

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
        self.ap_tools = hostAPServerTools()
        self.dns_tools = dnsmasqTools()

    def up(self):
        # bash_command(['service', 'wpa_supplicant', 'restart'])
        LOGGER.info(
            ['iw', 'wlan0', 'set', 'power_save', 'off']
        )
        LOGGER.info(backup_system_files())
        LOGGER.info(
            bash_command(
                ['iw', 'dev', 'wlan0', 'interface',
                 'add', 'uap0', 'type', '__ap']))
        LOGGER.info(
            write_network_interfaces(
                'wlan0', 'uap0', '172.24.1.1', 'bc:5f:f4:be:7d:0a'))
        LOGGER.info(
            write_dnsmasq('uap0', '172.24.1.1', '172.24.1.10', '172.24.1.20'))
        LOGGER.info(
            write_hostapd_conf(
                'uap0', 'nl80211', 'mycroft-doing-stuff', str(6)))
        LOGGER.info(
            write_default_hostapd('/etc/hostapd/hostapd.conf'))
        LOGGER.info(bash_command(['ifdown', 'wlan0']))
        LOGGER.info(bash_command(['ifup', 'wlan0']))
        LOGGER.info(bash_command(['ifdown', 'uap0']))
        LOGGER.info(bash_command(
            ['ip', 'link', 'set', 'dev', 'uap0',
             'address', 'bc:5f:f4:be:7d:0a']))
        LOGGER.info(bash_command(['ifup', 'uap0']))
        time.sleep(2)
        LOGGER.info(self.dns_tools.dnsmasqServiceStop())
        LOGGER.info(self.dns_tools.dnsmasqServiceStart())
        LOGGER.info(self.ap_tools.hostAPDStop())
        LOGGER.info(self.ap_tools.hostAPDStart())

    def down(self):
        LOGGER.info("ApAPI down Goes Here: ")
        LOGGER.info(self.ap_tools.hostAPDStop())
        LOGGER.info(self.dns_tools.dnsmasqServiceStop())
        LOGGER.info(restore_system_files())
        sys.exit()
