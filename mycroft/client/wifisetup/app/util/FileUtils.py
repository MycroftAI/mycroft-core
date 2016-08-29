#!/usr/bin/env python
import threading
from shutil import copyfile


class CopyFile(threading.Thread):
    def __init__(self, name, source_path, file_source, dest_path, file_dest):
        threading.Thread.__init__(self)
        self.name = name
        self.source_path = source_path
        self.file_source = file_source
        self.dest_path = dest_path
        self.file_dest = file_dest

    def run(self):
        try:
            copyfile(
                self.source_path + '/' + self.file_source,
                self.dest_path + '/' + self.file_dest)
        except:
            print self.name +\
                  " Failed -- file copy from: " +\
                  self.file_source + " to: "\
                  + self.file_dest


class WriteFileTemplate(threading.Thread):
    def __init__(self, name, file_name, template, context):
        threading.Thread.__init__(self)
        self.name = name
        self.file_name = file_name
        self.template = template
        self.context = context

    def run(self):
        print "Writing file template: " + self.file_name
        try:
            with open(self.file_name, 'w') as self.file:
                self.file.write(self.template.format(**self.context))
                self.file.close()
        except:
            print "FAIL: Writing file template: " + self.file_name
            return 1


def write_wpa_supplicant_conf(ssid, passphrase):
    template = """
country={country}
ctrl_interface=/var/run/wpa_supplicant
update_config=1
network={b1}
ssid={ssid}
psk={passphrase}
key_mgmt=WPA-PSK
{b2}
"""
    context = {
        "b1": '{',
        "b2": '}',
        "country": 'US',
        "ssid": ssid,
        "passphrase": passphrase
    }
    wpa_conf_write = WriteFileTemplate(
        'Write Wireless Settings to wpa_supplicant.conf ',
        '/etc/wpa_supplicant/wpa_supplicant.conf',
        template,
        context)
    wpa_conf_write.start()
    wpa_conf_write.join()


def write_hostapd_conf(interface, driver, ssid, channel):
    template = """interface={interface}
driver={driver}
ssid={ssid}
hw_mode=g
channel={channel}
ieee80211n=1
wmm_enabled=1
ht_capab=[HT40][SHORT-GI-20][DSSS_CCK-40]
macaddr_acl=0
ignore_broadcast_ssid=0
"""
    context = {
        "interface": interface,
        "driver": driver,
        "ssid": ssid,
        "channel": channel
    }
    hostapd_conf_write = WriteFileTemplate(
        'Write Access Point settings to hostapd.conf ',
        '/etc/hostapd/hostapd.conf',
        template,
        context)
    hostapd_conf_write.start()
    hostapd_conf_write.join()


def write_default_hostapd(config_file_path):
    template = """# Defaults for hostapd initscript
#
# See /usr/share/doc/hostapd/README.Debian for information about alternative
# methods of managing hostapd.
#
# Uncomment and set DAEMON_CONF to the absolute path of a hostapd configuration
# file and hostapd will be started during system boot. An example configuration
# file can be found at /usr/share/doc/hostapd/examples/hostapd.conf.gz
#
#DAEMON_CONF=""

# Additional daemon options to be appended to hostapd command:-
#       -d   show more debug messages (-dd for even more)
#       -K   include key data in debug messages
#       -t   include timestamps in some debug messages
#
# Note that -B (daemon mode) and -P (pidfile) options are automatically
# configured by the init.d script and must not be added to DAEMON_OPTS.
#
#DAEMON_OPTS=""
DAEMON_CONF="{config_file_path}"
"""
    context = {
        "config_file_path": config_file_path,
    }
    default_hostapd_write = WriteFileTemplate(
        'Write Access Point settings to hostapd.conf ',
        '/etc/default/hostapd',
        template,
        context)
    default_hostapd_write.start()
    default_hostapd_write.join()


def write_network_interfaces(wdev, vdev, vdev_address, vdev_hwaddress):
    template = """source-directory /etc/network/interfaces.d

auto lo
iface lo inet loopback

auto eth0
allow-hotplug eth0
iface eth0 inet dhcp

auto {wdev}
allow-hotplug {wdev}
iface {wdev} inet dhcp
    wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf

auto {vdev}
allow-hotplug {vdev}
iface {vdev} inet static
    address {vdev_address}
    netmask 255.255.255.0
    hwaddress ether {vdev_hwaddress}
"""
    context = {
        "wdev": wdev,
        "vdev": vdev,
        "vdev_address": vdev_address,
        "vdev_hwaddress": vdev_hwaddress
    }
    network_interfaces_write = WriteFileTemplate(
        'Write Network interface settings to ',
        '/etc/network/interfaces',
        template,
        context)
    network_interfaces_write.start()
    network_interfaces_write.join()


def write_dnsmasq(interface, server, dhcp_range_start, dhcp_range_end):
    template = """interface={interface}
bind-interfaces
server={server}
bogus-priv
dhcp-range={dhcp_range_start}, {dhcp_range_end}, 12h
address=/mycroft.ai/172.24.1.1
address=/#/172.24.1.1
    """

    context = {
        "interface": interface,
        "server": server,
        "dhcp_range_start": dhcp_range_start,
        "dhcp_range_end": dhcp_range_end
    }
    dns_conf_write = WriteFileTemplate('Write Network interface settings to ',
                                       '/etc/dnsmasq.conf',
                                       template, context)
    dns_conf_write.start()
    dns_conf_write.join()


def backup_system_files():
    backup_path = '/tmp'
    etc_network_interfaces = CopyFile('Backup - Network/Interfaces: ',
                                      '/etc/network/', 'interfaces',
                                      backup_path, 'out.net')
    etc_network_interfaces.start()
    etc_network_interfaces.join()

    etc_wpa_supplicant = CopyFile('Backup - Network/Interfaces: ',
                                  '/etc/wpa_supplicant/',
                                  'wpa_supplicant.conf',
                                  backup_path, 'out.wpa')
    etc_wpa_supplicant.start()
    etc_wpa_supplicant.join()

    etc_hostapd = CopyFile('Backup - HostAPD: ', '/etc/hostapd/',
                           'hostapd.conf', backup_path, 'out.ap')
    etc_hostapd.start()
    etc_hostapd.join()

    etc_default_hostapd = CopyFile('Backup - Default/HostAPD: ',
                                   '/etc/default/', 'hostapd',
                                   backup_path, 'out.default.ap')
    etc_default_hostapd.start()
    etc_default_hostapd.join()

    etc_dnsmasq = CopyFile('Backup - DNSMasq: ',
                           '/etc/',
                           'dnsmasq.conf',
                           backup_path,
                           'out.dnsmasq')
    etc_dnsmasq.start()
    etc_dnsmasq.join()


def restore_system_files():
    backup_path = '/tmp'
    etc_network_interfaces = CopyFile('Restore - Network/Interfaces: ',
                                      backup_path,
                                      'out.net',
                                      '/etc/network/',
                                      'interfaces')
    etc_network_interfaces.start()
    etc_network_interfaces.join()

    etc_hostapd = CopyFile('Restore - HostAPD: ', backup_path,
                           'out.ap', '/etc/hostapd/', 'hostapd.conf')
    etc_hostapd.start()
    etc_hostapd.join()

    etc_default_hostapd = CopyFile('Restore - Default/HostAPD: ',
                                   backup_path,
                                   'out.default.ap',
                                   '/etc/default/',
                                   'hostapd')
    etc_default_hostapd.start()
    etc_default_hostapd.join()

    etc_dnsmasq = CopyFile(
        'Restore - DNSMasq: ',
        backup_path,
        'out.dnsmasq',
        '/etc/',
        'dnsmasq.conf')
    etc_dnsmasq.start()
    etc_dnsmasq.join()


def ap_mode_config():
    backup_system_files()
    write_network_interfaces(
        'wlan0', 'uap0', '172.24.1.1', 'bc:5f:f4:be:7d:0a')
    write_hostapd_conf('uap0', 'nl80211', 'Mycroft-bing-bong-boom', 6)


def ap_mode_deconfig():
    restore_system_files()


def client_mode_config(iface, ssid, passphrase):
    write_wpa_supplicant_conf(ssid, passphrase)
