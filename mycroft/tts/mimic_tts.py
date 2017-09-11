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
import os
import os.path
from time import time, sleep
import unicodedata

from mycroft import MYCROFT_ROOT_PATH
from mycroft.configuration import ConfigurationManager
from mycroft.tts import TTS, TTSValidator
import mycroft.util
from mycroft.util.log import getLogger
LOGGER = getLogger(__name__)

__author__ = 'jdorleans', 'spenrod'

config = ConfigurationManager.get().get("tts").get("mimic")

BIN = config.get("path", os.path.join(MYCROFT_ROOT_PATH, 'mimic', 'bin',
                                      'mimic'))
if not os.path.isfile(BIN):
    # Search for mimic on the path
    import distutils.spawn
    BIN = distutils.spawn.find_executable("mimic")


class Mimic(TTS):
    def __init__(self, lang, voice):
        super(Mimic, self).__init__(lang, voice, MimicValidator(self))
        self.init_args()
        self.clear_cache()
        self.type = 'wav'

    def init_args(self):
        self.args = [BIN, '-voice', self.voice, '-psdur']
        stretch = config.get('duration_stretch', None)
        if stretch:
            self.args += ['--setf', 'duration_stretch=' + stretch]

    def get_tts(self, sentence, wav_file):
        # Generate WAV and phonemes
        phonemes = subprocess.check_output(self.args + ['-o', wav_file,
                                                        '-t', sentence])
        return wav_file, phonemes

    def visime(self, output):
        visimes = []
        start = time()
        pairs = output.split(" ")
        for pair in pairs:
            pho_dur = pair.split(":")  # phoneme:duration
            if len(pho_dur) == 2:
                visimes.append((VISIMES.get(pho_dur[0], '4'),
                                float(pho_dur[1])))
        return visimes


class MimicValidator(TTSValidator):
    def __init__(self, tts):
        super(MimicValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO: Verify version of mimic can handle the requested language
        pass

    def validate_connection(self):
        try:
            subprocess.call([BIN, '--version'])
        except:
            LOGGER.info("Failed to find mimic at: " + BIN)
            raise Exception(
                'Mimic was not found. Run install-mimic.sh to install it.')

    def get_tts_class(self):
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
