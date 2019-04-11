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

import os, requests, time
from mycroft.tts import TTS, TTSValidator
from mycroft.configuration import Configuration

class BingTTS(TTS):
    def __init__(self, lang, config):
        super(BingTTS, self).__init__(lang, config, BingTTSValidator(self))
        self.type = 'wav'
        self.config = Configuration.get().get("tts", {}).get("bing", {})
        api = self.config.get("api_key")
        self.subscription_key = self.config.get("api_key")
        self.access_token = None

    def get_tts(self, sentence, wav_file):
        fetch_token_url = "https://westus.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key
        }
        response = requests.post(fetch_token_url, headers=headers)
        self.access_token = str(response.text)

        base_url = 'https://westus.tts.speech.microsoft.com/'
        path = 'cognitiveservices/v1'
        constructed_url = base_url + path
        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm',
            'User-Agent': 'aiam-test',
            'cache-control': 'no-cache'
        }
        body = "<speak version='1.0' xml:lang='ar-SA'><voice xml:lang='ar-SA' xml:gender='Male' name='Microsoft Server Speech Text to Speech Voice (ar-SA, Naayf)'>" + sentence + "</voice></speak>"
        #body = "<speak version='1.0' xml:lang='ar-EG'><voice xml:lang='ar-EG' xml:gender='Female' name='Microsoft Server Speech Text to Speech Voice (ar-EG, Hoda)'>" + sentence + "</voice></speak>"

        response = requests.post(constructed_url, headers=headers, data=body.encode('utf-8'))

        with open(wav_file, 'wb') as audio:
            audio.write(response.content)
        return (wav_file, None)  # No phonemes

class BingTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(BingTTSValidator, self).__init__(tts)

    def validate_dependencies(self):
        pass

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        # TODO
        pass

    def get_tts_class(self):
        return BingTTS
