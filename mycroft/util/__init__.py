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


import os
import subprocess
from os.path import dirname
import socket

import psutil

__author__ = 'jdorleans'


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def play_wav(file_path):
    return subprocess.Popen(["aplay", file_path])


def play_mp3(file_path):
    return subprocess.Popen(["mpg123", file_path])


def record(file_path, duration, rate, channels):
    if duration > 0:
        return subprocess.Popen(
            ["arecord", "-r", str(rate), "-c", str(channels), "-d",
             str(duration), file_path])
    else:
        return subprocess.Popen(
            ["arecord", "-r", str(rate), "-c", str(channels), file_path])


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


class CerberusAccessDenied(Exception):
    pass
