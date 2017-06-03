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

from mycroft import MYCROFT_ROOT_PATH
from mycroft.tts import TTS, TTSValidator
from mycroft.configuration import ConfigurationManager

import time

import pymimic

__author__ = 'forslund'

# Provide path for non-standard mimic install
LIB = join(MYCROFT_ROOT_PATH, 'mimic-dev', 'lib')
pymimic.lib_paths.append(LIB)


class Pymimic(TTS):
    def __init__(self, lang, voice):
        super(Pymimic, self).__init__(lang, voice, PymimicValidator(self))
        self.voice = pymimic.Voice(voice)

    def execute(self, sentence):
        s = pymimic.Speak(str(sentence), self.voice)
        s.play()
        #  self.visime(s.phonemes)

    def visime(self, phoneme_pairs):
        for pair in phoneme_pairs:
            if check_for_signal('buttonPress'):
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
