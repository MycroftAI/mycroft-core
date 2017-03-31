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


import socket
import subprocess
import tempfile

import os
import os.path
import psutil
from os.path import dirname
from mycroft.util.log import getLogger
import mycroft.configuration

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


def resolve_resource_file(res_name):
    """Convert a resource into an absolute filename.

    Resource names are in the form: 'filename.ext'
    or 'path/filename.ext'

    The system wil look for ~/.mycroft/res_name first, and
    if not found will look at /opt/mycroft/res_name,
    then finally it will look for res_name in the 'mycroft/res'
    folder of the source code package.

    Example:
    With mycroft running as the user 'bob', if you called
        resolve_resource_file('snd/beep.wav')
    it would return either '/home/bob/.mycroft/snd/beep.wav' or
    '/opt/mycroft/snd/beep.wav' or '.../mycroft/res/snd/beep.wav',
    where the '...' is replaced by the path where the package has
    been installed.

    Args:
        res_name (str): a resource path/name
    """

    # First look for fully qualified file (e.g. a user setting)
    if os.path.isfile(res_name):
        return res_name

    # Now look for ~/.mycroft/res_name (in user folder)
    filename = os.path.expanduser("~/.mycroft/" + res_name)
    if os.path.isfile(filename):
        return filename

    # Next look for /opt/mycroft/res/res_name
    filename = os.path.expanduser("/opt/mycroft/" + res_name)
    if os.path.isfile(filename):
        return filename

    # Finally look for it in the source package
    filename = os.path.join(os.path.dirname(__file__), '..', 'res', res_name)
    filename = os.path.abspath(os.path.normpath(filename))
    if os.path.isfile(filename):
        return filename

    return None  # Resource cannot be resolved


def play_wav(uri):
    config = mycroft.configuration.ConfigurationManager.get()
    play_cmd = config.get("play_wav_cmdline")
    play_wav_cmd = str(play_cmd).split(" ")
    for index, cmd in enumerate(play_wav_cmd):
        if cmd == "%1":
            play_wav_cmd[index] = (get_http(uri))
    return subprocess.Popen(play_wav_cmd)


def play_mp3(uri):
    config = mycroft.configuration.ConfigurationManager.get()
    play_cmd = config.get("play_mp3_cmdline")
    play_mp3_cmd = str(play_cmd).split(" ")
    for index, cmd in enumerate(play_mp3_cmd):
        if cmd == "%1":
            play_mp3_cmd[index] = (get_http(uri))
    return subprocess.Popen(play_mp3_cmd)


def record(file_path, duration, rate, channels):
    if duration > 0:
        return subprocess.Popen(
            ["arecord", "-r", str(rate), "-c", str(channels), "-d",
             str(duration), file_path])
    else:
        return subprocess.Popen(
            ["arecord", "-r", str(rate), "-c", str(channels), file_path])


def get_http(uri):
    return uri.replace("https://", "http://")


def remove_last_slash(url):
    if url and url.endswith('/'):
        url = url[:-1]
    return url


def read_stripped_lines(filename):
    with open(filename, 'r') as f:
        return [line.strip() for line in f]


def read_dict(filename, div='='):
    d = {}
    with open(filename, 'r') as f:
        for line in f:
            (key, val) = line.split(div)
            d[key.strip()] = val.strip()
    return d


def create_file(filename):
    try:
        os.makedirs(dirname(filename))
    except OSError:
        pass
    with open(filename, 'w') as f:
        f.write('')


def kill(names):
    print psutil.pids()
    for name in names:
        for p in psutil.process_iter():
            try:
                if p.name() == name:
                    p.kill()
                    break
            except:
                pass


def connected(host="8.8.8.8", port=53, timeout=3):
    """
    Thanks to 7h3rAm on
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except IOError:
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
                ("8.8.4.4", port))
            return True
        except IOError:
            return False


def create_signal(signal_name):
    try:
        with open(tempfile.gettempdir() + '/' + signal_name, 'w'):
            return True
    except IOError:
        return False


def check_for_signal(signal_name):
    filename = tempfile.gettempdir() + '/' + signal_name
    if os.path.isfile(filename):
        os.remove(filename)
        return True
    return False


def validate_param(value, name):
    if not value:
        raise ValueError("Missing or empty %s in mycroft.conf " % name)
