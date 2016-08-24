from mycroft.client.wifisetup.app.util.hostAPDTools import hostAPServerTools
from mycroft.client.wifisetup.app.util.dnsmasqTools import dnsmasqTools
from mycroft.client.wifisetup.app.util.FileUtils import CopyFile, write_dnsmasq, write_hostapd_conf,\
    write_wpa_supplicant_conf, write_network_interfaces, backup_system_files, restore_system_files
from mycroft.client.wifisetup.app.util.wpaCLITools import wpaClientTools
from pyroute2 import IPRoute
# from mycroft.client.wifisetup.app.util.LinkUtils import dev_link_tools
from mycroft.client.wifisetup.app.util.bashThreadHandling import bash_command

#ap_tools = hostAPServerTools()
#dns_tools = dnsmasqTools()
ip = IPRoute()

class WiFiAPI():
    def __init__(self):
        self.none = None
        self.wpa_tools = wpaClientTools()

    def scan(self, iface):
        print "WiFi API Scan Goes Here"
        self.new_net = self.wpa_tools.wpa_cli_add_network('wlan0')


    def try_connect(self):
        print "WiFi API Connect Goes Here"


    def set_ssid(self, ssid):
        print "WiFi API Set SSID Goes Here: " + ssid
        self.wpa_tools.wpa_cli_set_network('wlan0', str(self.new_net), 'ssid', ssid)

    def set_psk(self, psk):
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
        bash_command('iw', 'dev', iface, 'interface', 'add', vap_id, 'type __ap')


class ApAPI():
    def __init__(self):
        self.none = None
        self.ap_tools = hostAPServerTools()
        self.dns_tools = dnsmasqTools()

    def up(self):
        print "APAPI up Goes Here: "
        print backup_system_files()
        print write_network_interfaces('wlan0', 'uap0', '172.24.1.1', 'bc:5f:f4:be:7d:0a')
        print write_dnsmasq('uap0', '172.24.1.1', '172.24.1.10', '172.24.1.20')
        print write_hostapd_conf('uap0', 'nl80211', 'mycroft-doing-stuff', str(6))
        print self.ap_tools.hostAPDStart()
        print self.dns_tools.dnsmasqServiceStart()

    def down(self):
        print "ApAPI down Goes Here: "
        print self.ap_tools.hostAPDStop()
        print self.dns_tools.dnsmasqServiceStop()
        print restore_system_files()


class FileAPI():
    def __init__(self):
        self.none = None

    def copy_file(self):
        print "FileAPI copyfile goes here "

    def backup_file(self):
        print "FileAPI backup_file goes here: "