from mycroft.client.wifisetup.app.util.hostAPDTools import hostAPServerTools
from mycroft.client.wifisetup.app.util.dnsmasqTools import dnsmasqTools
from mycroft.client.wifisetup.app.util.FileUtils import write_dnsmasq
from pyroute2 import IPRoute
# from mycroft.client.wifisetup.app.util.LinkUtils import dev_link_tools
from mycroft.client.wifisetup.app.util.bashThreadHandling import bash_command

#ap_tools = hostAPServerTools()
#dns_tools = dnsmasqTools()
ip = IPRoute()

class WiFiAPI():
    def __init__(self):
        self.none = None

    def scan(self, iface):
        print "WiFi API Scan Goes Here"

    def connect(self):
        print "WiFi API Connect Goes Here"

    def set_ssid(self, ssid):
        print "WiFi API Set SSID Goes Here: " + ssid

    def set_psk(self, psk):
        print "WiFi API Set PASSPHRASE Goes Here: " + psk

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
        bash_command('iw', 'dev', iface, 'interface add', vap_id, 'type __ap')


class ApAPI():
    def __init__(self):
        self.none = None
        self.ap_tools = hostAPServerTools()
        self.dns_tools = dnsmasqTools()

    def up(self):
        print "APAPI up Goes Here: "
        print write_dnsmasq('uap0','172.24.1.1', '172.24.1.10', '172.24.1.20')
        print self.ap_tools.hostAPDStart()
        print self.dns_tools.dnsmasqServiceStart()

    def down(self):
        print "ApAPI down Goes Here: "
        print self.ap_tools.hostAPDStop()
        print self.dns_tools.dnsmasqServiceStop()


class FileAPI():
    def __init__(self):
        self.none = None

    def copy_file(self):
        print "FileAPI copyfile goes here "
    def backup_file(self):
        print "FileAPI backup_file goes here: "