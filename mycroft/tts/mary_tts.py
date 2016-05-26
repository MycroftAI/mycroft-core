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


import requests

from mycroft.tts import TTSValidator
from mycroft.tts.remote_tts import RemoteTTS

__author__ = 'jdorleans'

NAME = 'marytts'


class MaryTTS(RemoteTTS):
    PARAMS = {
        'LOCALE': 'en_US',
        'VOICE': 'cmu-slt-hsmm',
        'INPUT_TEXT': 'Hello World',
        'INPUT_TYPE': 'TEXT',
        'AUDIO': 'WAVE_FILE',
        'OUTPUT_TYPE': 'AUDIO'
    }

    def __init__(self, lang, voice, url):
        super(MaryTTS, self).__init__(lang, voice, url, '/process')

    def build_request_params(self, sentence):
        params = self.PARAMS.copy()
        params['LOCALE'] = self.lang
        params['VOICE'] = self.voice
        params['INPUT_TEXT'] = sentence.encode('utf-8')
        return params


class MaryTTSValidator(TTSValidator):
    def __init__(self):
        super(MaryTTSValidator, self).__init__()

    def validate_lang(self, lang):
        # TODO
        pass

    def validate_connection(self, tts):
        try:
            resp = requests.get(tts.url + "/version", verify=False)
            if resp.content.find('Mary TTS server') < 0:
                raise Exception('Invalid MaryTTS server.')
        except:
            raise Exception(
                'MaryTTS server could not be verified. Check your connection '
                'to the server: ' + tts.url)

    def get_instance(self):
        return MaryTTS
