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
from .tts import TTS, TTSValidator
from mycroft.configuration import Configuration
from time import time
from mycroft.util.log import LOG


class BingTTS(TTS):
    def __init__(self, lang, config):
        super(BingTTS, self).__init__(lang, config, BingTTSValidator(self))
        self.type = 'wav'
        self.config = Configuration.get().get("tts", {}).get("bing", {})
        self.subscription_key = self.config.get("api_key", "")
        self.service_region = self.config.get("service_region", "centralus")
        self.voice = self.config.get("voice_name", "en-US-JennyNeural")
        self.format = self.config.get("format", "riff-24khz-16bit-mono-pcm")
        self.token = None
        self.token_ttl = 0

    def _get_token(self):
        if self.token and int(time()) < self.token_ttl:
            LOG.debug("BingTTS token is still alive")
            return self.token

        fetch_token_url = "https://{}.api.cognitive.microsoft.com/sts/v1.0/issueToken".format(self.service_region)
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key
        }
        response = requests.post(fetch_token_url, headers=headers)
        if response.status_code == 200:
            self.token = str(response.text)
            self.token_ttl = int(time()) + (9 * 60)
            LOG.debug("BingTTS get token success - new ttl: {}".format(self.token_ttl))
        else:
            self.token = None
            self.token_ttl = 0
            LOG.error("BingTTS request token failed with error code: {}".format(response.status_code))
        return self.token

    def get_tts(self, sentence, wav_file):
        tts_service_url = "https://{}.tts.speech.microsoft.com/cognitiveservices/v1".format(self.service_region)
        headers = {
            "Authorization": "Bearer {}".format(self._get_token()),
            "X-Microsoft-OutputFormat": self.format,
            "Content-Type": "application/ssml+xml",
            "User-Agent": "mycroft.ai open-source voice assistant"
        }
        lang = self.voice[0:4]
        xml = """
            <speak version='1.0' xml:lang='{}'><voice name='{}'>
            {}
            </voice></speak>
        """.format(lang, self.voice, sentence)
        response = requests.post(tts_service_url, data=xml.encode("utf-8"), headers=headers)
        if response.status_code != 200:
            LOG.error("BingTTS speech request failed with error code {}".format(response.status_code))
            return (None, None)
        LOG.debug("BingTTS speech request success: {}".format(response.status_code))
        output = response.content
        with open(wav_file, "wb") as f:
            f.write(output)
        return (wav_file, None)  # No phonemes


class BingTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(BingTTSValidator, self).__init__(tts)

    def validate_dependencies(self):
        # nothing todo
        pass

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            if not self.tts._get_token():
                raise Exception("BingTTS access token could not be retrieved. Please check your credentials")
        except TypeError:
            raise Exception(
                'BingTTS server could not be verified. Please check your '
                'internet connection.')

    def get_tts_class(self):
        return BingTTS
