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

from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
import psutil
import subprocess
import json
from time import time

__author__ = 'the7erm'

LOGGER = getLogger(__name__)


def and_(strings):
    """
    Join a list of strings with , and add 'and' at the end, because grammar
    matters.
    """
    if len(strings) <= 1:
        return " ".join(strings)

    return "%s and %s" % (", ".join(strings[0:-1]),
                          strings[-1])


def sizeof_fmt(num, suffix='Bytes'):
    # Stolen from: http://stackoverflow.com/a/1094933/2444609
    for unit in ['Bytes', 'Kilo bytes', 'Megs', 'Gig', 'Tera bytes',
                 'Peta bytes', 'Exa bytes', 'Yotta bytes']:
        if abs(num) < 1024.0:
            return "%3.1f %s" % (num, unit)
        num /= 1024.0

    return "%.1f %s" % (num, 'Yi')


class DiagnosticsSkill(MycroftSkill):

    def __init__(self):
        super(DiagnosticsSkill, self).__init__(name="DiagnosticsSkill")
        self.public_ip = None
        self.public_ip_expire = 0
        self.diagnostic_script = self.config.get('script')

    def initialize(self):
        self.load_data_files(dirname(__file__))

        cpu_intent = IntentBuilder("CpuIntent")\
            .require("CpuKeyword")\
            .build()
        self.register_intent(cpu_intent, self.handle_cpu_intent)

        drive_intent = IntentBuilder("DriveIntent")\
            .require("DriveSpaceKeyword")\
            .build()
        self.register_intent(drive_intent, self.handle_drive_intent)

        # There's already an IP skill.
        ip_intent = IntentBuilder("IpIntent")\
            .require("IpKeyword")\
            .build()
        self.register_intent(ip_intent, self.handle_ip_intent)

        uptime_intent = IntentBuilder("UptimeIntent")\
            .require("UptimeKeyword")\
            .build()
        self.register_intent(uptime_intent, self.handle_updtime_intent)

        custom_intent = IntentBuilder("CustomIntent")\
            .require("CustomKeyword")\
            .build()
        self.register_intent(custom_intent, self.handle_custom_intent)

    def handle_cpu_intent(self, message):
        data = {
            "percent": psutil.cpu_percent(interval=1)
        }
        self.speak_dialog("cpu", data)

    def handle_drive_intent(self, message):
        partitions = psutil.disk_partitions()
        for partition in partitions:
            partition_data = psutil.disk_usage(partition.mountpoint)
            # total=21378641920, used=4809781248, free=15482871808,
            # percent=22.5
            data = {
                "mountpoint": partition.mountpoint,
                "total": sizeof_fmt(partition_data.total),
                "used": sizeof_fmt(partition_data.used),
                "free": sizeof_fmt(partition_data.free),
                "percent": partition_data.percent
            }
            if partition_data.percent >= 90:
                self.speak_dialog("drive.low", data)
            else:
                self.speak_dialog("drive", data)

    def handle_ip_intent(self, message):
        ips = subprocess.check_output(['hostname', "-I"])
        ips = ips.strip()
        ips = ips.split(" ")

        public_json = subprocess.check_output([
            "wget", "-qO-",
            "https://api.ipify.org/?format=json"])

        public_ip = {
            "ip": "undetermined"
        }
        try:
            if self.public_ip is None or time() > self.public_ip_expire:
                public_ip = json.loads(public_json)
                self.public_ip = public_ip
                self.public_ip_expire = time() + 600
        except:
            pass
        data = {
            "ips": and_(ips),
            "public": public_ip.get("ip", "undetermined")
        }
        self.speak_dialog("ip", data)

    def handle_updtime_intent(self, message):
        uptime = subprocess.check_output(['uptime', '-p'])
        data = {
            'uptime': uptime.strip()
        }
        self.speak_dialog("uptime", data)

    def handle_custom_intent(self, message):
        if not self.diagnostic_script:
            self.speak_dialog("no.script")
            return

        self.speak_dialog("processing.script")
        result = subprocess.check_output([self.diagnostic_script])
        self.speak(result.strip())

    def stop(self):
        pass


def create_skill():
    return DiagnosticsSkill()
