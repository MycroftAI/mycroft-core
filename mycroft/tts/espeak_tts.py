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

from mycroft.tts import TTS, TTSValidator

__author__ = 'seanfitz', 'jdorleans'


class ESpeak(TTS):
    def __init__(self, lang, voice):
        super(ESpeak, self).__init__(lang, voice, ESpeakValidator(self))

    def execute(self, sentence):
        subprocess.call(
            ['espeak', '-v', self.lang + '+' + self.voice, sentence])


class ESpeakValidator(TTSValidator):
    def __init__(self, tts):
        super(ESpeakValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            subprocess.call(['espeak', '--version'])
        except:
            raise Exception(
                'ESpeak is not installed. Run: sudo apt-get install espeak')

    def get_tts_class(self):
        return ESpeak
