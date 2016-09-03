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

from mycroft import MYCROFT_ROOT_PATH
from mycroft.tts import TTS, TTSValidator
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message

__author__ = 'jdorleans'

config = ConfigurationManager.get().get("tts", {})

NAME = 'mimic'
BIN = config.get(
    "mimic.path", join(MYCROFT_ROOT_PATH, 'mimic', 'bin', 'mimic'))


def phonemes_start_stop(phonemes):
    """ Reduces phonemes to a start speaking and a stop speaking value. """
    if len(phonemes) > 1:
        return [('start', phonemes[0][1]), ('stop', phonemes[-1][1])]
    else:
        return []


def phonemes_speaking(phonemes):
    """ Reduces phonemes to pauses and speaking intervals """
    binary = []
    for e in phonemes:
        if e[0] != 'pau':
            new = ('speaking', e[1])
        else:
            new = e
        if len(binary) == 0 or binary[-1][0] != new[0]:
            binary.append(new)
        else:
            binary[-1] = new
    return binary


def phonemes_all(phonemes):
    """ Keeps all phoneme data """
    return phonemes


def phonemes_none(phonemes):
    """ Removes all phoneme data """
    return []

phoneme_set = {'all': phonemes_all,
               'startstop': phonemes_start_stop,
               'speaking': phonemes_speaking,
               'none': phonemes_none
               }


class Mimic(TTS):
    def __init__(self, lang, voice):
        super(Mimic, self).__init__(lang, voice)
        pf = config.get('mimic.phonemes', 'none')
        self.representation = phoneme_set.get(pf, phonemes_none)

    def execute(self, sentence, client):
        process = subprocess.Popen(['stdbuf', '-oL', BIN,
                                    '-psdur', '-voice', self.voice,
                                   '-t', sentence], stdout=subprocess.PIPE)
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                phonemes = output.strip().split(' ')
                phonemes = [(e.split(':')[0], e.split(':')[1])
                            for e in phonemes]
                phonemes = self.representation(phonemes)
                if len(phonemes) > 0:
                    client.emit(Message('mycroft.tts',
                                        metadata={'phonemes': phonemes}))


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
