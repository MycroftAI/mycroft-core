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

import subprocess
import sys
import threading


class cmd_thread(threading.Thread):
    def __init__(self, cmd):
        threading.Thread.__init__(self)
        self.cmd = cmd
        self._return = "No Output"

    def run(self):
        try:
            proc = subprocess.Popen(self.cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            if stdout:
                self._return = {
                    'exit': 0, 'returncode': proc.returncode, 'stdout': stdout}
            if stderr:
                self._return = {'exit': 0,
                                'returncode': proc.returncode,
                                'stdout': stderr}
        except OSError as e:
            self._return = {'exit': 1,
                            'os_errno': e.errno,
                            'os_stderr': e.strerror,
                            'os_filename': e.filename}
        except:
            self._return = {'exit': 2, 'sys': sys.exc_info()[0]}

    def join(self, timeout=None):
        threading.Thread.join(self)
        return self._return


def bash_command(command):
    proc = cmd_thread(command)
    proc.start()
    return proc.join()
