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
from __future__ import absolute_import

import json
import logging
import os
import re
import requests
import signal as sig
import socket
import subprocess
import tempfile
from copy import deepcopy
from stat import S_ISREG, ST_MTIME, ST_MODE, ST_SIZE
from threading import Thread
from time import sleep
from urllib.request import urlopen
from urllib.error import URLError

import pyaudio
import psutil

import mycroft.audio
import mycroft.configuration
from mycroft.util.format import nice_number
# Officially exported methods from this file:
# play_wav, play_mp3, play_ogg, get_cache_directory,
# resolve_resource_file, wait_while_speaking
from mycroft.util.log import LOG
from mycroft.util.parse import extract_datetime, extract_number, normalize
# TODO: Other modules import signals functions from here, make consistent
from mycroft.util.signal import (
    create_file,
    check_for_signal,
    create_signal,
    ensure_directory_exists,
    get_ipc_directory
)


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
    Returns:
        str: path to resource or None if no resource found
    """
    config = mycroft.configuration.Configuration.get()

    # First look for fully qualified file (e.g. a user setting)
    if os.path.isfile(res_name):
        return res_name

    # Now look for ~/.mycroft/res_name (in user folder)
    filename = os.path.expanduser("~/.mycroft/" + res_name)
    if os.path.isfile(filename):
        return filename

    # Next look for /opt/mycroft/res/res_name
    data_dir = os.path.expanduser(config['data_dir'])
    filename = os.path.expanduser(os.path.join(data_dir, res_name))
    if os.path.isfile(filename):
        return filename

    # Finally look for it in the source package
    filename = os.path.join(os.path.dirname(__file__), '..', 'res', res_name)
    filename = os.path.abspath(os.path.normpath(filename))
    if os.path.isfile(filename):
        return filename

    return None  # Resource cannot be resolved


def play_audio_file(uri: str, environment=None):
    """ Play an audio file.

    This wraps the other play_* functions, choosing the correct one based on
    the file extension. The function will return directly and play the file
    in the background.

    Arguments:
        uri:    uri to play
        environment (dict): optional environment for the subprocess call

    Returns: subprocess.Popen object. None if the format is not supported or
             an error occurs playing the file.

    """
    extension_to_function = {
        '.wav': play_wav,
        '.mp3': play_mp3,
        '.ogg': play_ogg
    }
    _, extension = os.path.splitext(uri)
    play_function = extension_to_function.get(extension.lower())
    if play_function:
        return play_function(uri, environment)
    else:
        LOG.error("Could not find a function capable of playing {uri}."
                  " Supported formats are {keys}."
                  .format(uri=uri, keys=list(extension_to_function.keys())))
        return None


_ENVIRONMENT = deepcopy(os.environ)
_ENVIRONMENT['PULSE_PROP'] = 'media.role=music'


def _get_pulse_environment(config):
    """Return environment for pulse audio depeding on ducking config."""
    tts_config = config.get('tts', {})
    if tts_config and tts_config.get('pulse_duck'):
        return _ENVIRONMENT
    else:
        return os.environ


def play_wav(uri, environment=None):
    """ Play a wav-file.

        This will use the application specified in the mycroft config
        and play the uri passed as argument. The function will return directly
        and play the file in the background.

        Arguments:
            uri:    uri to play
            environment (dict): optional environment for the subprocess call

        Returns: subprocess.Popen object
    """
    config = mycroft.configuration.Configuration.get()
    environment = environment or _get_pulse_environment(config)
    play_cmd = config.get("play_wav_cmdline")
    play_wav_cmd = str(play_cmd).split(" ")
    for index, cmd in enumerate(play_wav_cmd):
        if cmd == "%1":
            play_wav_cmd[index] = (get_http(uri))
    try:
        return subprocess.Popen(play_wav_cmd, env=environment)
    except Exception as e:
        LOG.error("Failed to launch WAV: {}".format(play_wav_cmd))
        LOG.debug("Error: {}".format(repr(e)), exc_info=True)
        return None


def play_mp3(uri, environment=None):
    """ Play a mp3-file.

        This will use the application specified in the mycroft config
        and play the uri passed as argument. The function will return directly
        and play the file in the background.

        Arguments:
            uri:    uri to play
            environment (dict): optional environment for the subprocess call

        Returns: subprocess.Popen object
    """
    config = mycroft.configuration.Configuration.get()
    environment = environment or _get_pulse_environment(config)
    play_cmd = config.get("play_mp3_cmdline")
    play_mp3_cmd = str(play_cmd).split(" ")
    for index, cmd in enumerate(play_mp3_cmd):
        if cmd == "%1":
            play_mp3_cmd[index] = (get_http(uri))
    try:
        return subprocess.Popen(play_mp3_cmd, env=environment)
    except Exception as e:
        LOG.error("Failed to launch MP3: {}".format(play_mp3_cmd))
        LOG.debug("Error: {}".format(repr(e)), exc_info=True)
        return None


def play_ogg(uri, environment=None):
    """ Play a ogg-file.

        This will use the application specified in the mycroft config
        and play the uri passed as argument. The function will return directly
        and play the file in the background.

        Arguments:
            uri:    uri to play
            environment (dict): optional environment for the subprocess call

        Returns: subprocess.Popen object
    """
    config = mycroft.configuration.Configuration.get()
    environment = environment or _get_pulse_environment(config)
    play_cmd = config.get("play_ogg_cmdline")
    play_ogg_cmd = str(play_cmd).split(" ")
    for index, cmd in enumerate(play_ogg_cmd):
        if cmd == "%1":
            play_ogg_cmd[index] = (get_http(uri))
    try:
        return subprocess.Popen(play_ogg_cmd, env=environment)
    except Exception as e:
        LOG.error("Failed to launch OGG: {}".format(play_ogg_cmd))
        LOG.debug("Error: {}".format(repr(e)), exc_info=True)
        return None


def record(file_path, duration, rate, channels):
    if duration > 0:
        return subprocess.Popen(
            ["arecord", "-r", str(rate), "-c", str(channels), "-d",
             str(duration), file_path])
    else:
        return subprocess.Popen(
            ["arecord", "-r", str(rate), "-c", str(channels), file_path])


def find_input_device(device_name):
    """ Find audio input device by name.

        Arguments:
            device_name: device name or regex pattern to match

        Returns: device_index (int) or None if device wasn't found
    """
    LOG.info('Searching for input device: {}'.format(device_name))
    LOG.debug('Devices: ')
    pa = pyaudio.PyAudio()
    pattern = re.compile(device_name)
    for device_index in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(device_index)
        LOG.debug('   {}'.format(dev['name']))
        if dev['maxInputChannels'] > 0 and pattern.match(dev['name']):
            LOG.debug('    ^-- matched')
            return device_index
    return None


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


def connected():
    """ Check connection by connecting to 8.8.8.8 and if google.com is
    reachable if this fails, Check Microsoft NCSI is used as a backup.

    Returns:
        True if internet connection can be detected
    """
    if _connected_dns():
        # Outside IP is reachable check if names are resolvable
        return _connected_google()
    else:
        # DNS can't be reached, do a complete fetch in case it's blocked
        return _connected_ncsi()


def _connected_ncsi():
    """ Check internet connection by retrieving the Microsoft NCSI endpoint.

    Returns:
        True if internet connection can be detected
    """
    try:
        r = requests.get('http://www.msftncsi.com/ncsi.txt')
        if r.text == 'Microsoft NCSI':
            return True
    except Exception:
        pass
    return False


def _connected_dns(host="8.8.8.8", port=53, timeout=3):
    """ Check internet connection by connecting to DNS servers

    Returns:
        True if internet connection can be detected
    """
    # Thanks to 7h3rAm on
    # Host: 8.8.8.8 (google-public-dns-a.google.com)
    # OpenPort: 53/tcp
    # Service: domain (DNS/TCP)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        return True
    except IOError:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect(("8.8.4.4", port))
            return True
        except IOError:
            return False


def _connected_google():
    """Check internet connection by connecting to www.google.com
    Returns:
        True if connection attempt succeeded
    """
    connect_success = False
    try:
        urlopen('https://www.google.com', timeout=3)
    except URLError as ue:
        LOG.debug('Attempt to connect to internet failed: ' + str(ue.reason))
    else:
        connect_success = True

    return connect_success


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
            except Exception:
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


def reset_sigint_handler():
    """
    Reset the sigint handler to the default. This fixes KeyboardInterrupt
    not getting raised when started via start-mycroft.sh
    """
    sig.signal(sig.SIGINT, sig.default_int_handler)


def create_daemon(target, args=(), kwargs=None):
    """Helper to quickly create and start a thread with daemon = True"""
    t = Thread(target=target, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
    return t


def wait_for_exit_signal():
    """Blocks until KeyboardInterrupt is received"""
    try:
        while True:
            sleep(100)
    except KeyboardInterrupt:
        pass


_log_all_bus_messages = False


def create_echo_function(name, whitelist=None):
    """ Standard logging mechanism for Mycroft processes.

    This handles the setup of the basic logging for all Mycroft
    messagebus-based processes.

    Args:
        name (str): Reference name of the process
        whitelist (list, optional): List of "type" strings.  If defined, only
                                    messages in this list will be logged.

    Returns:
        func: The echo function
    """

    from mycroft.configuration import Configuration
    blacklist = Configuration.get().get("ignore_logs")

    # Make sure whitelisting doesn't remove the log level setting command
    if whitelist:
        whitelist.append('mycroft.debug.log')

    def echo(message):
        global _log_all_bus_messages
        try:
            msg = json.loads(message)
            msg_type = msg.get("type", "")
            # Whitelist match beginning of message
            # i.e 'mycroft.audio.service' will allow the message
            # 'mycroft.audio.service.play' for example
            if whitelist and not any([msg_type.startswith(e)
                                     for e in whitelist]):
                return

            if blacklist and msg_type in blacklist:
                return

            if msg_type == "mycroft.debug.log":
                # Respond to requests to adjust the logger settings
                lvl = msg["data"].get("level", "").upper()
                if lvl in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
                    LOG.level = lvl
                    LOG(name).info("Changing log level to: {}".format(lvl))
                    try:
                        logging.getLogger().setLevel(lvl)
                        logging.getLogger('urllib3').setLevel(lvl)
                    except Exception:
                        pass  # We don't really care about if this fails...
                else:
                    LOG(name).info("Invalid level provided: {}".format(lvl))

                # Allow enable/disable of messagebus traffic
                log_bus = msg["data"].get("bus", None)
                if log_bus is not None:
                    LOG(name).info("Bus logging: {}".format(log_bus))
                    _log_all_bus_messages = log_bus
            elif msg_type == "registration":
                # do not log tokens from registration messages
                msg["data"]["token"] = None
                message = json.dumps(msg)
        except Exception as e:
            LOG.info("Error: {}".format(repr(e)), exc_info=True)

        if _log_all_bus_messages:
            # Listen for messages and echo them for logging
            LOG(name).info("BUS: {}".format(message))
    return echo


def camel_case_split(identifier: str) -> str:
    """Split camel case string"""
    regex = '.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)'
    matches = re.finditer(regex, identifier)
    return ' '.join([m.group(0) for m in matches])
