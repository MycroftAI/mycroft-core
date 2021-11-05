# Copyright 2019 Mycroft AI Inc.
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

from .tts import TTS, TTSValidator
from mycroft.configuration import Configuration

import requests

_API_URL = "https://voice.mcs.mail.ru/tts"


class VkTTS(TTS):
    def __init__(self, lang, config):
        super(VkTTS, self).__init__(lang, config, VkTTSValidator(self), "mp3")
        self.encoder = "mp3"
        self.config = Configuration.get().get("tts", {}).get("vk", {})
        self.service_token = self.config.get("service_token")
        self.tempo = self.config.get("tempo", 1.0)

    def get_tts(self, sentence, wav_file):
        with open(wav_file, "wb") as f:
            for audio_content in self._synthesize(sentence):
                f.write(audio_content)
        return (wav_file, None)  # No phonemes

    def _synthesize(self, text):
        headers = {"Authorization": "Bearer {}".format(self.service_token)}

        params = {
            "text": text,
            "tempo": self.tempo,
            "encoder": self.encoder
        }

        with requests.get(_API_URL, params=params, headers=headers,
                          stream=True) as resp:
            if resp.status_code != 200:
                raise Exception(
                    "Request to VK TTS failed: code: {}, body: {}".format(
                        resp.status_code, resp.text))

            for chunk in resp.iter_content(chunk_size=None):
                yield chunk


class VkTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(VkTTSValidator, self).__init__(tts)

    def validate_lang(self):
        pass

    def validate_connection(self):
        config = Configuration.get().get("tts", {}).get("vk", {})
        service_token = config.get("service_token")
        if service_token is not None:
            headers = {"Authorization": "Bearer {}".format(service_token)}
            r = requests.get(_API_URL, headers=headers)
            if r.status_code == 400:  # Authorized, but bad request
                return True
            elif r.status_code == 401:  # Unauthorized
                raise Exception("Invalid service token for VK TTS")
            else:
                raise Exception(
                    "Unexpected HTTP code from VK Cloud TTS ({})".format(
                        r.status_code))
        else:
            raise ValueError("Service token for VK Cloud TTS is not defined")

    def get_tts_class(self):
        return VkTTS
