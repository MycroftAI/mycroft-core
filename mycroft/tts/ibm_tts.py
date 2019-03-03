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

from mycroft.tts import TTSValidator
from mycroft.tts.remote_tts import RemoteTTS
from mycroft.configuration import Configuration
from requests.auth import HTTPBasicAuth


class WatsonTTS(RemoteTTS):
    PARAMS = {'accept': 'audio/wav'}

    def __init__(self, lang, config,
                 url="https://stream.watsonplatform.net/text-to-speech/api"):
        super(WatsonTTS, self).__init__(lang, config, url, '/v1/synthesize',
                                        WatsonTTSValidator(self))
        self.type = "wav"
        user = self.config.get("user") or self.config.get("username")
        password = self.config.get("password")
        api_key = self.config.get("apikey")
        if api_key is None:
            self.auth = HTTPBasicAuth(user, password)
        else:
            self.auth = HTTPBasicAuth("apikey", api_key)

    def build_request_params(self, sentence):
        params = self.PARAMS.copy()
        params['LOCALE'] = self.lang
        params['voice'] = self.voice
        params['text'] = sentence.encode('utf-8')
        return params


class WatsonTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(WatsonTTSValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        config = Configuration.get().get("tts", {}).get("watson", {})
        user = config.get("user") or config.get("username")
        password = config.get("password")
        apikey = config.get("apikey")
        if user and password or apikey:
            return
        else:
            raise ValueError('user/pass or apikey for IBM tts is not defined')

    def get_tts_class(self):
        return WatsonTTS
