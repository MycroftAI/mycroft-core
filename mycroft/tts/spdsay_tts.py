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

__author__ = 'jdorleans'


class SpdSay(TTS):
    def __init__(self, lang, voice):
        super(SpdSay, self).__init__(lang, voice, SpdSayValidator(self))

    def execute(self, sentence):
        subprocess.call(
            ['spd-say', '-l', self.lang, '-t', self.voice, sentence])


class SpdSayValidator(TTSValidator):
    def __init__(self, tts):
        super(SpdSayValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            subprocess.call(['spd-say', '--version'])
        except:
            raise Exception(
                'SpdSay is not installed. Run: sudo apt-get install '
                'speech-dispatcher')

    def get_tts_class(self):
        return SpdSay
