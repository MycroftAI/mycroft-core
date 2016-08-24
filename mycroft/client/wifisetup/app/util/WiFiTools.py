from subprocess import Popen, PIPE
import httplib
from pyroute2 import IPRoute

ip = IPRoute()


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
        with open(
                '/etc/wpa_supplicant/wpa_supplicant.conf', 'w'
        ) as self.myfile:
            self.myfile.write(self.template.format(**self.context))
            self.myfile.close()
        try:
            print bash_command(["ip addr flush wlan0"])

            print bash_command(["ifdown wlan0"])
            # bash_command(['ifconfig wlan0 up'])
            print bash_command(["ifup wlan0"])
        except:
            print "connection failed"


class hostapd_tools():
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
        # bash_command(["pkill -f 'dnsmasq'"])

    def hostapd_start(self):
        print bash_command(["systemctl", "start", "hostapd.service"])
        # print bash_command(["hostapd /etc/hostapd/hostapd.conf"])

    def hostapd_stop(self):
        print bash_command(['systemctl', 'stop', 'hostapd.service'])
        # bash_command(["pfkill -f 'hostapd'"])


def bash_command(cmd):
    print cmd
    # try:
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    proc.wait()
    # stdout,stderr = proc.communicate()
    return proc.returncode
