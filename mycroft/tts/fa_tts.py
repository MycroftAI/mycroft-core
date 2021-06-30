# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import requests

from mycroft.tts.tts import TTSValidator
from mycroft.tts.remote_tts import RemoteTTS


class FATTS(RemoteTTS):
    PARAMS = {
        'voice[name]': 'cmu-slt-hsmm',
        'input[type]': 'TEXT',
        'input[locale]': 'en_US',
        'input[content]': 'Hello World',
        'output[format]': 'WAVE_FILE',
        'output[type]': 'AUDIO'
    }

    def __init__(self, lang, config):
        super(FATTS, self).__init__(lang, config, '/say',
                                    FATTSValidator(self))

    def build_request_params(self, sentence):
        params = self.PARAMS.copy()
        params['voice[name]'] = self.voice
        params['input[locale]'] = self.lang
        params['input[content]'] = sentence.encode('utf-8')
        return params


class FATTSValidator(TTSValidator):
    def __init__(self, tts):
        super(FATTSValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            resp = requests.get(self.tts.url + "/info/version", verify=False)
            content = resp.json()
            if content.get('product', '').find('FA-TTS') < 0:
                raise Exception('Invalid FA-TTS server.')
        except Exception:
            raise Exception(
                'FA-TTS server could not be verified. Check your connection '
                'to the server: ' + self.tts.url)

    def get_tts_class(self):
        return FATTS
