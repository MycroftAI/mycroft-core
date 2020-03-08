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
import argparse
import os
import pyaudio
from contextlib import contextmanager

from speech_recognition import Recognizer

from mycroft.client.speech.mic import MutableMicrophone
from mycroft.configuration import Configuration
from mycroft.util.audio_utils import play_wav
from mycroft.util.log import LOG
import logging

"""
Audio Test
A tool for recording X seconds of audio, and then playing them back. Useful
for testing hardware, and ensures
compatibility with mycroft recognizer loop code.
"""

# Reduce loglevel
LOG.level = 'ERROR'
logging.getLogger('urllib3').setLevel(logging.WARNING)


@contextmanager
def mute_output():
    """ Context manager blocking stdout and stderr completely.

    Redirects stdout and stderr to dev-null and restores them on exit.
    """
    # Open a pair of null files
    null_fds = [os.open(os.devnull, os.O_RDWR) for i in range(2)]
    # Save the actual stdout (1) and stderr (2) file  descriptors.
    orig_fds = [os.dup(1), os.dup(2)]
    # Assign the null pointers to stdout and stderr.
    os.dup2(null_fds[0], 1)
    os.dup2(null_fds[1], 2)
    try:
        yield
    finally:
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(orig_fds[0], 1)
        os.dup2(orig_fds[1], 2)
        for fd in null_fds + orig_fds:
            os.close(fd)


def record(filename, duration):
    mic = MutableMicrophone()
    recognizer = Recognizer()
    with mic as source:
        audio = recognizer.record(source, duration=duration)
        with open(filename, 'wb') as f:
            f.write(audio.get_wav_data())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f', '--filename', dest='filename', default="/tmp/test.wav",
        help="Filename for saved audio (Default: /tmp/test.wav)")
    parser.add_argument(
        '-d', '--duration', dest='duration', type=int, default=10,
        help="Duration of recording in seconds (Default: 10)")
    parser.add_argument(
        '-v', '--verbose', dest='verbose', action='store_true', default=False,
        help="Add extra output regarding the recording")
    parser.add_argument(
        '-l', '--list', dest='show_devices', action='store_true',
        default=False, help="List all availabile input devices")
    args = parser.parse_args()

    if args.show_devices:
        print(" Initializing... ")
        pa = pyaudio.PyAudio()

        print(" ====================== Audio Devices ======================")
        print("  Index    Device Name")
        for device_index in range(pa.get_device_count()):
            dev = pa.get_device_info_by_index(device_index)
            if dev['maxInputChannels'] > 0:
                print('   {}:       {}'.format(device_index, dev['name']))
        print()

    config = Configuration.get()
    if "device_name" in config["listener"]:
        dev = config["listener"]["device_name"]
    elif "device_index" in config["listener"]:
        dev = "Device at index {}".format(config["listener"]["device_index"])
    else:
        dev = "Default device"
    samplerate = config["listener"]["sample_rate"]
    play_cmd = config["play_wav_cmdline"].replace("%1", "WAV_FILE")
    print(" ========================== Info ===========================")
    print(" Input device: {} @ Sample rate: {} Hz".format(dev, samplerate))
    print(" Playback commandline: {}".format(play_cmd))
    print()
    print(" ===========================================================")
    print(" ==         STARTING TO RECORD, MAKE SOME NOISE!          ==")
    print(" ===========================================================")

    if not args.verbose:
        with mute_output():
            record(args.filename, args.duration)
    else:
        record(args.filename, args.duration)

    print(" ===========================================================")
    print(" ==           DONE RECORDING, PLAYING BACK...             ==")
    print(" ===========================================================")
    status = play_wav(args.filename).wait()
    if status:
        print('An error occured while playing back audio ({})'.format(status))


if __name__ == "__main__":
    main()
