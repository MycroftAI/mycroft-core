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

"""
Configuration:
`$ mycroft-config edit user`
{
    ...
    "lang": "eu-eu",
    "tts": {
        "module": "elhuyar",
        "elhuyar": {
            "token": "xxxxx", (required)
            "genre": "F|M", (optional)
            "speed": 100 (optional)
        }
    }
}
"""

from .tts import TTSValidator
from .remote_tts import RemoteTTS


class ElhuyarTTS(RemoteTTS):
    def __init__(self, lang, config):
        super(ElhuyarTTS, self).__init__(lang, config, 'http://tts.elhuyar.eus',
            '/ahots_sintesia/ahots_sintesia/', ElhuyarTTSValidator(self))
        self.token = config.get('token')
        self.gender = config.get('gender', 'M')
        self.speed = config.get('speed', 100)

    def build_request_params(self, sentence):
        return {
            'testua': sentence.encode('utf-8'),
            'kodea': self.token,
            'speed': self.speed,
            'gender': self.gender,
            # Lang for Elhuyar TTS:`eu-eu` -> `eu`
            'hizkuntza': self.lang.split('-')[0],
            'response': 'wav'
        }

    def _RemoteTTS__request(self, p):
        return self.session.post(
            self.url + self.api_path, data=self.build_request_params(p),
            timeout=10, verify=False, auth=self.auth)


class ElhuyarTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(ElhuyarTTSValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        # TODO
        pass

    def get_tts_class(self):
        return ElhuyarTTS
