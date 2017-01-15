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


from gtts import gTTS

from mycroft.tts import TTS, TTSValidator
from mycroft.util import play_mp3

__author__ = 'jdorleans'


class GoogleTTS(TTS):
    def __init__(self, lang, voice):
        super(GoogleTTS, self).__init__(lang, voice, GoogleTTSValidator(self))

    def execute(self, sentence):
        tts = gTTS(sentence, self.lang)
        tts.save(self.filename)
        p = play_mp3(self.filename)
        p.communicate()  # Wait for termination


class GoogleTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(GoogleTTSValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            gTTS(text='Hi').save(self.tts.filename)
        except:
            raise Exception(
                'GoogleTTS server could not be verified. Please check your '
                'internet connection.')

    def get_tts_class(self):
        return GoogleTTS
