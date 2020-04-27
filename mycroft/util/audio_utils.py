# Copyright 2020 Mycroft AI Inc.
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
"""Contains simple tools for performing audio related tasks such as playback
of audio, recording and listing devices.
"""
from copy import deepcopy
import os
import pyaudio
import re
import subprocess

import mycroft.configuration
from .string_utils import get_http
from .log import LOG


def play_audio_file(uri: str, environment=None):
    """Play an audio file.

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


# Create a custom environment to use that can be ducked by a phone role.
# This is kept separate from the normal os.environ to ensure that the TTS
# role isn't affected and that any thirdparty software launched through
# a mycroft process can select if they wish to honor this.
_ENVIRONMENT = deepcopy(os.environ)
_ENVIRONMENT['PULSE_PROP'] = 'media.role=music'


def _get_pulse_environment(config):
    """Return environment for pulse audio depeding on ducking config."""
    tts_config = config.get('tts', {})
    if tts_config and tts_config.get('pulse_duck'):
        return _ENVIRONMENT
    else:
        return os.environ


def _play_cmd(cmd, uri, config, environment):
    """Generic function for starting playback from a commandline and uri.

    Arguments:
        cmd (str): commandline to execute %1 in the command line will be
                   replaced with the provided uri.
        uri (str): uri to play
        config (dict): config to use
        environment: environment to execute in, can be used to supply specific
                     pulseaudio settings.
    """
    environment = environment or _get_pulse_environment(config)
    cmd_elements = str(cmd).split(" ")
    cmdline = [e if e != '%1' else get_http(uri) for e in cmd_elements]
    return subprocess.Popen(cmdline, env=environment)


def play_wav(uri, environment=None):
    """Play a wav-file.

    This will use the application specified in the mycroft config
    and play the uri passed as argument. The function will return directly
    and play the file in the background.

    Arguments:
        uri:    uri to play
        environment (dict): optional environment for the subprocess call

    Returns: subprocess.Popen object or None if operation failed
    """
    config = mycroft.configuration.Configuration.get()
    play_wav_cmd = config['play_wav_cmdline']
    try:
        return _play_cmd(play_wav_cmd, uri, config, environment)
    except FileNotFoundError as e:
        LOG.error("Failed to launch WAV: {} ({})".format(play_wav_cmd,
                                                         repr(e)))
    except Exception:
        LOG.exception("Failed to launch WAV: {}".format(play_wav_cmd))
    return None


def play_mp3(uri, environment=None):
    """Play a mp3-file.

    This will use the application specified in the mycroft config
    and play the uri passed as argument. The function will return directly
    and play the file in the background.

    Arguments:
        uri:    uri to play
        environment (dict): optional environment for the subprocess call

    Returns: subprocess.Popen object or None if operation failed
    """
    config = mycroft.configuration.Configuration.get()
    play_mp3_cmd = config.get("play_mp3_cmdline")
    try:
        return _play_cmd(play_mp3_cmd, uri, config, environment)
    except FileNotFoundError as e:
        LOG.error("Failed to launch MP3: {} ({})".format(play_mp3_cmd,
                                                         repr(e)))
    except Exception:
        LOG.exception("Failed to launch MP3: {}".format(play_mp3_cmd))
    return None


def play_ogg(uri, environment=None):
    """Play an ogg-file.

    This will use the application specified in the mycroft config
    and play the uri passed as argument. The function will return directly
    and play the file in the background.

    Arguments:
        uri:    uri to play
        environment (dict): optional environment for the subprocess call

    Returns: subprocess.Popen object, or None if operation failed
    """
    config = mycroft.configuration.Configuration.get()
    play_ogg_cmd = config.get("play_ogg_cmdline")
    try:
        return _play_cmd(play_ogg_cmd, uri, config, environment)
    except FileNotFoundError as e:
        LOG.error("Failed to launch OGG: {} ({})".format(play_ogg_cmd,
                                                         repr(e)))
    except Exception:
        LOG.exception("Failed to launch OGG: {}".format(play_ogg_cmd))
    return None


def record(file_path, duration, rate, channels):
    """Simple function to record from the default mic.

    The recording is done in the background by the arecord commandline
    application.

    Arguments:
        file_path: where to store the recorded data
        duration: how long to record
        rate: sample rate
        channels: number of channels

    Returns:
        process for performing the recording.
    """
    command = ['arecord', '-r', str(rate), '-c', str(channels)]
    command += ['-d', str(duration)] if duration > 0 else []
    command += [file_path]
    return subprocess.Popen(command)


def find_input_device(device_name):
    """Find audio input device by name.

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
