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
"""Mimic TTS, a local TTS backend.

This Backend uses the mimic executable to render text into speech.
"""
import os
import os.path
from os.path import exists, join, expanduser
import stat
import subprocess
from threading import Thread
from time import sleep

from mycroft import MYCROFT_ROOT_PATH
from mycroft.api import DeviceApi
from mycroft.configuration import Configuration
from mycroft.util.download import download
from mycroft.util.log import LOG

from .tts import TTS, TTSValidator

CONFIG = Configuration.get().get("tts").get("mimic")
DATA_DIR = expanduser(Configuration.get()['data_dir'])

BIN = CONFIG.get("path",
                 os.path.join(MYCROFT_ROOT_PATH, 'mimic', 'bin', 'mimic'))

if not os.path.isfile(BIN):
    # Search for mimic on the path
    import distutils.spawn

    BIN = distutils.spawn.find_executable("mimic")

SUBSCRIBER_VOICES = {'trinity': join(DATA_DIR, 'voices/mimic_tn')}


def download_subscriber_voices(selected_voice):
    """Function to download all premium voices.

    The function starts with the currently selected if applicable
    """

    def make_executable(dest):
        """Call back function to make the downloaded file executable."""
        LOG.info('Make executable new voice binary executable')
        # make executable
        file_stat = os.stat(dest)
        os.chmod(dest, file_stat.st_mode | stat.S_IEXEC)

    # First download the selected voice if needed
    voice_file = SUBSCRIBER_VOICES.get(selected_voice)
    if voice_file is not None and not exists(voice_file):
        LOG.info('Voice doesn\'t exist, downloading')
        url = DeviceApi().get_subscriber_voice_url(selected_voice)
        # Check we got an url
        if url:
            dl_status = download(url, voice_file, make_executable)
            # Wait for completion
            while not dl_status.done:
                sleep(1)
        else:
            LOG.debug('{} is not available for this architecture'
                      .format(selected_voice))

    # Download the rest of the subsciber voices as needed
    for voice in SUBSCRIBER_VOICES:
        voice_file = SUBSCRIBER_VOICES[voice]
        if not exists(voice_file):
            url = DeviceApi().get_subscriber_voice_url(voice)
            # Check we got an url
            if url:
                dl_status = download(url, voice_file, make_executable)
                # Wait for completion
                while not dl_status.done:
                    sleep(1)
            else:
                LOG.debug('{} is not available for this architecture'
                          .format(voice))


class Mimic(TTS):
    """TTS interface for local mimic v1."""
    def __init__(self, lang, config):
        super(Mimic, self).__init__(
            lang, config, MimicValidator(self), 'wav',
            ssml_tags=["speak", "ssml", "phoneme", "voice", "audio", "prosody"]
        )
        self.clear_cache()

        # Download subscriber voices if needed
        self.is_subscriber = DeviceApi().is_subscriber
        if self.is_subscriber:
            trd = Thread(target=download_subscriber_voices, args=[self.voice])
            trd.daemon = True
            trd.start()

    def modify_tag(self, tag):
        """Modify the SSML to suite Mimic."""
        ssml_conversions = {
            'x-slow': '0.4',
            'slow': '0.7',
            'medium': '1.0',
            'high': '1.3',
            'x-high': '1.6',
            'speed': 'rate'
        }
        for key, value in ssml_conversions.items():
            tag = tag.replace(key, value)
        return tag

    @property
    def args(self):
        """Build mimic arguments."""
        if (self.voice in SUBSCRIBER_VOICES and
                exists(SUBSCRIBER_VOICES[self.voice]) and self.is_subscriber):
            # Use subscriber voice
            mimic_bin = SUBSCRIBER_VOICES[self.voice]
            voice = self.voice
        elif self.voice in SUBSCRIBER_VOICES:
            # Premium voice but bin doesn't exist, use ap while downloading
            mimic_bin = BIN
            voice = 'ap'
        else:
            # Normal case use normal binary and selected voice
            mimic_bin = BIN
            voice = self.voice

        args = [mimic_bin, '-voice', voice, '-psdur', '-ssml']

        stretch = self.config.get('duration_stretch', None)
        if stretch:
            args += ['--setf', 'duration_stretch={}'.format(stretch)]
        return args

    def get_tts(self, sentence, wav_file):
        """Generate WAV and phonemes.

        Arguments:
            sentence (str): sentence to generate audio for
            wav_file (str): output file

        Returns:
            tuple ((str) file location, (str) generated phonemes)
        """
        phonemes = subprocess.check_output(self.args + ['-o', wav_file,
                                                        '-t', sentence])
        return wav_file, phonemes.decode()

    def viseme(self, output):
        """Convert phoneme string to visemes.

        Arguments:
            output (str): Phoneme output from mimic

        Returns:
            (list) list of tuples of viseme and duration
        """
        visemes = []
        pairs = str(output).split(" ")
        for pair in pairs:
            pho_dur = pair.split(":")  # phoneme:duration
            if len(pho_dur) == 2:
                visemes.append((VISIMES.get(pho_dur[0], '4'),
                                float(pho_dur[1])))
        return visemes


class MimicValidator(TTSValidator):
    """Validator class checking that Mimic can be used."""
    def validate_lang(self):
        """Verify that the language is supported."""
        # TODO: Verify version of mimic can handle the requested language

    def validate_connection(self):
        """Check that Mimic executable is found and works."""
        try:
            subprocess.call([BIN, '--version'])
        except Exception as err:
            if BIN:
                LOG.error('Failed to find mimic at: {}'.format(BIN))
            else:
                LOG.error('Mimic executable not found')
            raise Exception(
                'Mimic was not found. Run install-mimic.sh to install it.') \
                from err

    def get_tts_class(self):
        """Return the TTS class associated with the validator."""
        return Mimic


# Mapping based on Jeffers phoneme to viseme map, seen in table 1 from:
# http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.221.6377&rep=rep1&type=pdf
#
# Mycroft unit visemes based on images found at:
# http://www.web3.lu/wp-content/uploads/2014/09/visemes.jpg
#
# Mapping was created partially based on the "12 mouth shapes visuals seen at:
# https://wolfpaulus.com/journal/software/lipsynchronization/

VISIMES = {
    # /A group
    'v': '5',
    'f': '5',
    # /B group
    'uh': '2',
    'w': '2',
    'uw': '2',
    'er': '2',
    'r': '2',
    'ow': '2',
    # /C group
    'b': '4',
    'p': '4',
    'm': '4',
    # /D group
    'aw': '1',
    # /E group
    'th': '3',
    'dh': '3',
    # /F group
    'zh': '3',
    'ch': '3',
    'sh': '3',
    'jh': '3',
    # /G group
    'oy': '6',
    'ao': '6',
    # /Hgroup
    'z': '3',
    's': '3',
    # /I group
    'ae': '0',
    'eh': '0',
    'ey': '0',
    'ah': '0',
    'ih': '0',
    'y': '0',
    'iy': '0',
    'aa': '0',
    'ay': '0',
    'ax': '0',
    'hh': '0',
    # /J group
    'n': '3',
    't': '3',
    'd': '3',
    'l': '3',
    # /K group
    'g': '3',
    'ng': '3',
    'k': '3',
    # blank mouth
    'pau': '4',
}
