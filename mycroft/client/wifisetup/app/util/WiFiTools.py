from subprocess import Popen, PIPE
from socket import AF_INET
import httplib
from pyroute2 import IPRoute
from wifi import Cell, Scheme
from Config import AppConfig
from collections import defaultdict
#app_config = './configuration/default.ini'

#config = AppConfig()
#ip = IPRoute()

#config.open_file(app_config)
#config.create_section('wifi')
#config.set_option('wifi','iface','wlan0')
#config.set_option('wifi','iface','wlp3s0')
#config.write_file(app_config)
config = AppConfig()
ip = IPRoute()

# wifi schem



class ap_link_tools():
    def __init_(self):
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
        with  open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as self.myfile:
            self.myfile.write(self.template.format(**self.context))
            self.myfile.close()
        try:
            print bash_command(["ip addr flush wlan0"])

            print bash_command(["ifdown wlan0"])

            #bash_command(['ifconfig wlan0 up'])
            #rint bash_command(["wpa_supplicant -iwlan0 -Dnl80211 -c /etc/wpa_supplicant/wpa_supplicant.conf"])
            print bash_command(["ifup wlan0"])
        except:
            print "connection failed"



class hostapd_tools():
    def ap_config(self):
        bash_command('bash -x /home/pi/rpi3-headless-wifi-setup/hostapd-shell/config-change-ap-on.sh')
    def ap_deconfig(self):
        bash_command('bash -x  /home/pi/rpi3-headless-wifi-setup/hostapd-shell/config-change-restore.sh')
    def ap_up(self):
        bash_command('bash -x /home/pi/rpi3-headless-wifi-setup/hostapd-shell/ap-up.sh')
    def ap_down(self):
        bash_command('bash -x /home/pi/rpi3-headless-wifi-setup/hostapd-shell/ap-down.sh')
    def dnsmasq_start(self):
        bash_command(["systemctl", "start", "dnsmasq.service"])
        #bash_command(["dnsmasq -D --interface=uap0 --dhcp-range=uap0,172.24.1.1,172.24.1.1,255.255.255.0"])

    def dnsmasq_stop(self):
        bash_command(["systemctl", "stop", "dnsmasq.service"])
        #bash_command(["pkill -f 'dnsmasq'"])

    def hostapd_start(self):
        print bash_command(["systemctl", "start", "hostapd.service"])
        #print bash_command(["hostapd /etc/hostapd/hostapd.conf"])

    def hostapd_stop(self):
        print bash_command(['systemctl', 'stop', 'hostapd.service'])
        #bash_command(["pfkill -f 'hostapd'"])


class dev_link_tools():
#    interface = config.ConfigSectionMap("wifi")['iface']
    def __init__(self):
        pass

    def link_add(self):
        interface = config.ConfigSectionMap("wifi-ap")['iface']
        dev = ip.link_lookup(ifname=link)[0]

    def link_up(self, link):
        interface = config.ConfigSectionMap("wifi-ap")['iface']
        dev = ip.link_lookup(ifname=link)[0]
        ip.link('set', index=dev,
            state='up')

    def link_down(self, link):
        interface = config.ConfigSectionMap("wifi-ap")['iface']
        dev = ip.link_lookup(ifname=interface)[0]
        ip.link('set', index=dev,
            state='down')
    def link_add_vap(self):
        print bash_command('iw dev wlan0 interface add uap0 type __ap')
        print bash_command('ifdown upa0')
        print bash_command('ifup upa0')

def bash_command(cmd):
    print cmd
    #try:
    proc = Popen(cmd, shell=True , stdout=PIPE, stderr=PIPE)
    proc.wait()
    #stdout,stderr = proc.communicate()
    return proc.returncode


    #except stderr:
        #print stdout, stderr
