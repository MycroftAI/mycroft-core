# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import socket
import subprocess

import os.path
import psutil
from stat import S_ISREG, ST_MTIME, ST_MODE, ST_SIZE

import mycroft.audio
import mycroft.configuration
from mycroft.util.format import nice_number
# Officially exported methods from this file:
# play_wav, play_mp3, get_cache_directory,
# resolve_resource_file, wait_while_speaking
from mycroft.util.log import LOG
from mycroft.util.parse import extract_datetime, extractnumber, normalize
from mycroft.util.signal import *


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
    config = mycroft.configuration.Configuration.get()
    play_cmd = config.get("play_wav_cmdline")
    play_wav_cmd = str(play_cmd).split(" ")
    for index, cmd in enumerate(play_wav_cmd):
        if cmd == "%1":
            play_wav_cmd[index] = (get_http(uri))
    return subprocess.Popen(play_wav_cmd)


def play_mp3(uri):
    config = mycroft.configuration.Configuration.get()
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


def connected(host="8.8.8.8", port=53, timeout=3):
    """
    Thanks to 7h3rAm on
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)

    NOTE:
    This is no longer in use by this version
    New method checks for a connection using ConnectionError only when
    a question is asked
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


def curate_cache(directory, min_free_percent=5.0, min_free_disk=50):
    """Clear out the directory if needed

    This assumes all the files in the directory can be deleted as freely

    Args:
        directory (str): directory path that holds cached files
        min_free_percent (float): percentage (0.0-100.0) of drive to keep free,
                                  default is 5% if not specified.
        min_free_disk (float): minimum allowed disk space in MB, default
                               value is 50 MB if not specified.
    """

    # Simpleminded implementation -- keep a certain percentage of the
    # disk available.
    # TODO: Would be easy to add more options, like whitelisted files, etc.
    space = psutil.disk_usage(directory)

    # convert from MB to bytes
    min_free_disk *= 1024 * 1024
    # space.percent = space.used/space.total*100.0
    percent_free = 100.0 - space.percent
    if percent_free < min_free_percent and space.free < min_free_disk:
        LOG.info('Low diskspace detected, cleaning cache')
        # calculate how many bytes we need to delete
        bytes_needed = (min_free_percent - percent_free) / 100.0 * space.total
        bytes_needed = int(bytes_needed + 1.0)

        # get all entries in the directory w/ stats
        entries = (os.path.join(directory, fn) for fn in os.listdir(directory))
        entries = ((os.stat(path), path) for path in entries)

        # leave only regular files, insert modification date
        entries = ((stat[ST_MTIME], stat[ST_SIZE], path)
                   for stat, path in entries if S_ISREG(stat[ST_MODE]))

        # delete files with oldest modification date until space is freed
        space_freed = 0
        for moddate, fsize, path in sorted(entries):
            try:
                os.remove(path)
                space_freed += fsize
            except:
                pass

            if space_freed > bytes_needed:
                return  # deleted enough!


def get_cache_directory(domain=None):
    """Get a directory for caching data

    This directory can be used to hold temporary caches of data to
    speed up performance.  This directory will likely be part of a
    small RAM disk and may be cleared at any time.  So code that
    uses these cached files must be able to fallback and regenerate
    the file.

    Args:
        domain (str): The cache domain.  Basically just a subdirectory.

    Return:
        str: a path to the directory where you can cache data
    """
    config = mycroft.configuration.Configuration.get()
    dir = config.get("cache_path")
    if not dir:
        # If not defined, use /tmp/mycroft/cache
        dir = os.path.join(tempfile.gettempdir(), "mycroft", "cache")
    return ensure_directory_exists(dir, domain)


def validate_param(value, name):
    if not value:
        raise ValueError("Missing or empty %s in mycroft.conf " % name)


def is_speaking():
    """Determine if Text to Speech is occurring

    Returns:
        bool: True while still speaking
    """
    LOG.info("mycroft.utils.is_speaking() is depreciated, use "
             "mycroft.audio.is_speaking() instead.")
    return mycroft.audio.is_speaking()


def wait_while_speaking():
    """Pause as long as Text to Speech is still happening

    Pause while Text to Speech is still happening.  This always pauses
    briefly to ensure that any preceeding request to speak has time to
    begin.
    """
    LOG.info("mycroft.utils.wait_while_speaking() is depreciated, use "
             "mycroft.audio.wait_while_speaking() instead.")
    return mycroft.audio.wait_while_speaking()


def stop_speaking():
    # TODO: Less hacky approach to this once Audio Manager is implemented
    # Skills should only be able to stop speech they've initiated
    LOG.info("mycroft.utils.stop_speaking() is depreciated, use "
             "mycroft.audio.stop_speaking() instead.")
    mycroft.audio.stop_speaking()


def get_arch():
    """ Get architecture string of system. """
    return os.uname()[4]
