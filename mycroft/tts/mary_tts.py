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


class MaryTTS(RemoteTTS):
    PARAMS = {
        'LOCALE': 'en_US',
        'VOICE': 'cmu-slt-hsmm',
        'INPUT_TEXT': 'Hello World',
        'INPUT_TYPE': 'TEXT',
        'AUDIO': 'WAVE_FILE',
        'OUTPUT_TYPE': 'AUDIO'
    }

    def __init__(self, lang, config):
        super(MaryTTS, self).__init__(lang, config, config.get('url'),
                                      '/process', MaryTTSValidator(self))

    def build_request_params(self, sentence):
        params = self.PARAMS.copy()
        params['LOCALE'] = self.lang
        params['VOICE'] = self.voice
        params['INPUT_TEXT'] = sentence.encode('utf-8')
        return params


class MaryTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(MaryTTSValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            resp = requests.get(self.tts.url + "/version", verify=False)
            if resp.status_code == 200:
                return True
        except Exception:
            raise Exception(
                'MaryTTS server could not be verified. Check your connection '
                'to the server: ' + self.tts.url)

    def get_tts_class(self):
        return MaryTTS
