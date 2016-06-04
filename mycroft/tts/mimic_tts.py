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

from mycroft import MYCROFT_ROOT_PATH
from mycroft.tts import TTS, TTSValidator
from mycroft.configuration.config import ConfigurationManager

__author__ = 'jdorleans'

config = ConfigurationManager.get().get("tts", {})

NAME = 'mimic'
BIN = config.get(
    "mimic.path", join(MYCROFT_ROOT_PATH, 'mimic', 'bin', 'mimic'))


class Mimic(TTS):
    def __init__(self, lang, voice):
        super(Mimic, self).__init__(lang, voice)

    def execute(self, sentence):
        subprocess.call([BIN, '-voice', self.voice, '-t', sentence])


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
