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


def write_dnsmasq(interface, server, dhcp_range_start, dhcp_range_end):
    template = """interface={interface}
bind-interfaces
server={server}
domain-needed
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

    copy_file(
        'Restore - DNSMasq: ',
        backup_path, 'out.dnsmasq',
        '/etc/', 'dnsmasq.conf')


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
