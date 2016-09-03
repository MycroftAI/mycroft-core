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

from shutil import copyfile


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
    write_file('/etc/hostapd/hostapd.conf', template, context)


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
    write_file('/etc/default/hostapd', template, context)


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
    write_file('/etc/dnsmasq.conf', template, context)


def restore_system_files():
    backup_path = '/tmp'
    copy_file('Restore - Network/Interfaces: ',
              backup_path,
              'out.net',
              '/etc/network/',
              'interfaces')

    copy_file('Restore - HostAPD: ', backup_path,
              'out.ap', '/etc/hostapd/', 'hostapd.conf')

    copy_file('Restore - Default/HostAPD: ',
              backup_path,
              'out.default.ap',
              '/etc/default/',
              'hostapd')

    copy_file(
        'Restore - DNSMasq: ',
        backup_path,
        'out.dnsmasq',
        '/etc/',
        'dnsmasq.conf')


def write_file(file_name, template, context):
    print "Writing file template: " + file_name
    try:
        with open(file_name, 'w') as f:
            f.write(template.format(**context))
            f.close()
    except:
        print "FAIL: Writing file template: " + file_name
        return 1


def copy_file(name, source_path, file_source, dest_path, file_dest):
    try:
        copyfile(
            source_path + '/' + file_source,
            dest_path + '/' + file_dest)
    except:
        print name + \
              " Failed -- file copy from: " + \
              file_source + " to: " \
              + file_dest
