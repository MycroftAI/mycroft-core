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
from os.path import join
import os
import hashlib

from mycroft import MYCROFT_ROOT_PATH
from mycroft.tts import TTS, TTSValidator
from mycroft.configuration import ConfigurationManager
import mycroft.util
from mycroft.util.log import getLogger

from time import time, sleep

import pymimic

__author__ = 'forslund'

LOGGER = getLogger(__name__)
# Provide path for non-standard mimic install
LIB = join(MYCROFT_ROOT_PATH, 'mimic', 'lib')
pymimic.lib_paths.append(LIB)


class Pymimic(TTS):
    def __init__(self, lang, voice):
        super(Pymimic, self).__init__(lang, voice, PymimicValidator(self))
        self.voice = pymimic.Voice(voice)

    def get_tts(self, sentence):
        key = str(hashlib.md5(sentence.encode('utf-8', 'ignore')).hexdigest())
        wav_file = os.path.join(mycroft.util.get_cache_directory("tts"),
                                key + ".wav")

        if os.path.exists(wav_file):
            phonemes = self.load_phonemes(key)
            if phonemes:
                # Using cached value
                LOGGER.debug("TTS cache hit")
                return wav_file, phonemes

        # Generate WAV and phonemes
        s = pymimic.Speak(str(sentence), self.voice)
        s.write(wav_file)
        self.save_phonemes(key, s.phonemes)
        return wav_file, s.phonemes

    def save_phonemes(self, key, phonemes):
        # Clean out the cache as needed
        s = ''
        for p in phonemes:
            s += p[0] + ':' + str(p[1]) + ' '
        s = s.strip()
        cache_dir = mycroft.util.get_cache_directory("tts")
        mycroft.util.curate_cache(cache_dir)

        pho_file = os.path.join(cache_dir, key+".pho")
        try:
            with open(pho_file, "w") as cachefile:
                cachefile.write(s)
        except:
            LOGGER.debug("Failed to write .PHO to cache")
            pass

    def load_phonemes(self, key):
        pho_file = os.path.join(mycroft.util.get_cache_directory("tts"),
                                key+".pho")
        if os.path.exists(pho_file):
            try:
                phonemes = []
                with open(pho_file, 'r') as cachefile:
                    string = cachefile.read().strip()
                    pairs = string.split(' ')
                    for pair in pairs:
                        phonemes.append(pair.split(':'))

                return phonemes
            except:
                LOGGER.error("Failed to read .PHO from cache", exc_info=True)
        return None

    def execute(self, sentence):
        wav_file, phonemes = self.get_tts(sentence)

        self.blink(0.5)
        process = mycroft.util.play_wav(wav_file)
        self.visime(phonemes)
        process.communicate()
        self.blink(0.2)

    def visime(self, phoneme_pairs):
        start = time()
        for pair in phoneme_pairs:
            if mycroft.util.check_for_signal('buttonPress'):
                return
            code = VISIMES.get(pair[0], '4')
            print code, pair[1]
            self.enclosure.mouth_viseme(code)
            duration = float(pair[1])
            delta = time() - start
            if delta < duration:
                sleep(duration - delta)


class PymimicValidator(TTSValidator):
    def __init__(self, tts):
        super(PymimicValidator, self).__init__(tts)

    def validate_lang(self):
        pass

    def validate_connection(self):
        pass

    def get_tts_class(self):
        return Pymimic


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
