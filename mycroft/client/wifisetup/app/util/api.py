import time
from pyroute2 import IPRoute

from mycroft.client.wifisetup.app.util.hostAPDTools import hostAPServerTools
from mycroft.client.wifisetup.app.util.dnsmasqTools import dnsmasqTools
from mycroft.client.wifisetup.app.util.FileUtils import write_dnsmasq,\
    write_hostapd_conf, write_wpa_supplicant_conf, write_network_interfaces,\
    backup_system_files, restore_system_files, write_default_hostapd
from mycroft.client.wifisetup.app.util.wpaCLITools import wpaClientTools
from mycroft.client.wifisetup.app.util.bashThreadHandling import bash_command


ip = IPRoute()


class WiFiAPI():
    def __init__(self):
        self.none = None
        self.wpa_tools = wpaClientTools()
        self.ssid = None
        self.passphrase = None

    def scan(self, iface):
        print "WiFi API Scan Goes Here"
        self.new_net = self.wpa_tools.wpa_cli_add_network('wlan0')

    def try_connect(self):
        print "WiFi API Connect Goes Here"
        self.ssid = '"' + self.ssid + '"'
        self.passphrase = '"' + self.passphrase + '"'
        print self.ssid
        print self.passphrase
        network_id = self.wpa_tools.wpa_cli_add_network('wlan0')['stdout']
        print self.wpa_tools.wpa_cli_set_network(
            'wlan0', network_id, 'ssid', self.ssid)
        print self.wpa_tools.wpa_cli_set_network(
            'wlan0', network_id, 'psk', self.passphrase)
        print self.wpa_tools.wpa_cli_enable_network('wlan0', network_id)
        connected = False
        while connected is False:
            for i in range(22):
                time.sleep(1)
                try:
                    state = self.wpa_tools.wpa_cli_status('wlan0')['wpa_state']
                    if state == 'COMPLETED':
                        print "COMPLETED"
                        connected = True
                        return True
                    else:
                        connected = False
                except:
                    print "No state yet: waiting for timeout"
                    pass
            if connected is False:
                return False

    def set_ssid(self, ssid):
        self.ssid = ssid
        self.wpa_tools.wpa_cli_set_network(
            'wlan0', str(self.new_net), 'ssid', ssid)

    def set_psk(self, psk):
        self.passphrase = psk
        print "WiFi API Set PASSPHRASE Goes Here: " + psk
        self.wpa_tools.wpa_cli_set_network('wlan0', str(self.new_net), '', psk)

    def save_wpa_network(self, ssid, password):
        print write_wpa_supplicant_conf(ssid, password)


class LinkAPI():
    def __init__(self):
        self.none = None

    def link_up(self, iface):
        print "WiFi API Link Up goes here: " + iface
        print bash_command(['ifup', iface])

    def link_down(self, iface):
        print "WiFi API Link down goes here: " + iface
        print bash_command(['ifdown', iface])

    def create_vap(self, iface, vap_id):
        print "WiFi API create vap goes here: " + iface + vap_id
        bash_command(
            'iw', 'dev', iface, 'interface', 'add', vap_id, 'type __ap')


class ApAPI():
    def __init__(self):
        self.none = None
        self.ap_tools = hostAPServerTools()
        self.dns_tools = dnsmasqTools()

    def up(self):
        print backup_system_files()
        print bash_command(
            ['iw', 'dev', 'wlan0', 'interface', 'add', 'uap0', 'type', '__ap'])
        print write_network_interfaces(
            'wlan0', 'uap0', '172.24.1.1', 'bc:5f:f4:be:7d:0a')
        print write_dnsmasq(
            'uap0', '172.24.1.1', '172.24.1.10', '172.24.1.20')
        print write_hostapd_conf(
            'uap0', 'nl80211', 'mycroft-doing-stuff', str(6))
        print write_default_hostapd('/etc/hostapd/hostapd.conf')
        print bash_command(['ifdown', 'wlan0'])
        print bash_command(['ifup', 'wlan0'])
        print bash_command(['ifdown', 'uap0'])
        print bash_command(
            ['ip', 'link', 'set', 'dev', 'uap0',
             'address', 'bc:5f:f4:be:7d:0a'])
        print bash_command(['ifup', 'uap0'])
        time.sleep(2)
        print self.dns_tools.dnsmasqServiceStop()
        print self.dns_tools.dnsmasqServiceStart()
        print self.ap_tools.hostAPDStop()
        print self.ap_tools.hostAPDStart()

    def down(self):
        print "ApAPI down Goes Here: "
        # print self.ap_tools.hostAPDStop()
        print bash_command({'pkill', '-f', '"wifi"'})
        print self.ap_tools.hostAPDStop()
        print self.dns_tools.dnsmasqServiceStop()
        print restore_system_files()
