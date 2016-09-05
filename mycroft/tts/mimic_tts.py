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
from os.path import join
import re
import random
import os
import time

from mycroft import MYCROFT_ROOT_PATH
from mycroft.tts import TTS, TTSValidator
from mycroft.configuration import ConfigurationManager
from mycroft.client.enclosure.api import EnclosureAPI

__author__ = 'jdorleans'

config = ConfigurationManager.get().get("tts", {})

NAME = 'mimic'
BIN = config.get(
    "mimic.path", join(MYCROFT_ROOT_PATH, 'mimic', 'bin', 'mimic'))

# Mapping based on Jeffers phoneme to viseme map, seen in table 1 from:
# http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.221.6377&rep=rep1&type=pdf
#
# Mycroft unit visemes based on images found at:
#   http://www.web3.lu/wp-content/uploads/2014/09/visemes.jpg
# and mapping was created partially based on the "12 mouth shapes"
# visuals seen at:
#   https://wolfpaulus.com/journal/software/lipsynchronization/
# with final viseme group to image mapping by Steve Penrod


class Mimic(TTS):

    def __init__(self, lang, voice):
        super(Mimic, self).__init__(lang, voice)

    def PhonemeToViseme(self, pho):
        return {
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
        }.get(pho, '4')    # 4 is default if pho not found

    def execute(self, sentence, client):
        enclosure = EnclosureAPI(client)

        random.seed()
        # blink 50% of the time before speaking (only shows up if the
        # mimic TTS generation takes fairly long)
        if (random.random() < 0.5):
            enclosure.eyes_blink("b")

        # invoke mimic, creating WAV and outputting phoneme:duration pairs
        outMimic = subprocess.check_output([BIN, '-voice', self.voice, '-t',
                                            sentence, '-psdur', "-o",
                                            "/tmp/mimic.wav"])

        # split into parts
        lisPairs = outMimic.split(" ")

        # covert phonemes to visemes
        visCodes = ''
        for pair in lisPairs:
            pho_dur = pair.split(":")
            if len(pho_dur) != 2:
                continue
            visCodes += self.PhonemeToViseme(pho_dur[0]) + ":"
            visCodes += pho_dur[1] + ","

        # play WAV and walk thru visemes while it plays
        enclosure.mouth_viseme(visCodes)
        subprocess.call(['aplay', '/tmp/mimic.wav'])

        # after speaking, blink 20% of the time
        if (random.random() < 0.2):
            enclosure.eyes_blink("b")

        # delete WAV
        os.remove("/tmp/mimic.wav")


class MimicValidator(TTSValidator):
    def __init__(self):
        super(MimicValidator, self).__init__()

    def validate_lang(self, lang):
        pass

    def validate_connection(self, tts):
        try:
            subprocess.call([BIN, '--version'])
        except:
            raise Exception(
                'Mimic is not installed. Make sure install-mimic.sh ran '
                'properly.')

    def get_instance(self):
        return Mimic
