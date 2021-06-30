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

from mycroft.tts.tts import TTS, TTSValidator
from mycroft.configuration import Configuration

import requests
import wave

_API_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


class YandexTTS(TTS):
    def __init__(self, lang, config):
        super(YandexTTS, self).__init__(lang, config, YandexTTSValidator(self))
        self.type = "wav"
        self.config = Configuration.get().get("tts", {}).get("yandex", {})
        self.api_key = self.config.get("api_key")
        self.voice = self.config.get("voice", "oksana")
        self.emotion = self.config.get("emotion", "neutral")
        self.speed = self.config.get("speed", 1.0)
        self.sample_rate = self.config.get("sample_rate", 48000)

    def get_tts(self, sentence, wav_file):
        with wave.open(wav_file, "wb") as f:
            f.setparams((1, 2, self.sample_rate, 0, "NONE", "NONE"))
            for audio_content in self._synthesize(sentence):
                f.writeframes(audio_content)
        return (wav_file, None)  # No phonemes

    # Based on example: https://cloud.yandex.com/docs/speechkit/tts/request#wav
    def _synthesize(self, text):
        headers = {"Authorization": "Api-Key {}".format(self.api_key)}

        data = {
            "text": text,
            "lang": self.lang,
            "voice": self.voice,
            "emotion": self.emotion,
            "speed": self.speed,
            "format": "lpcm",
            "sampleRateHertz": self.sample_rate
        }

        with requests.post(_API_URL, headers=headers, data=data,
                           stream=True) as resp:
            if resp.status_code != 200:
                raise Exception(
                    "Request to Yandex TTS failed: code: {}, body: {}".format(
                        resp.status_code, resp.text))

            for chunk in resp.iter_content(chunk_size=None):
                yield chunk


class YandexTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(YandexTTSValidator, self).__init__(tts)

    def validate_lang(self):
        config = Configuration.get().get("tts", {}).get("yandex", {})
        lang = config.get("lang")
        if lang in ["en-US", "ru-RU", "tr-TR"]:
            return True
        raise ValueError("Unsupported language for Yandex TTS")

    def validate_connection(self):
        config = Configuration.get().get("tts", {}).get("yandex", {})
        api_key = config.get("api_key")
        if api_key is not None:
            headers = {"Authorization": "Api-Key {}".format(api_key)}
            r = requests.get(_API_URL, headers=headers)
            if r.status_code == 400:  # Authorized, but bad request
                return True
            elif r.status_code == 401:  # Unauthorized
                raise Exception("Invalid API key for Yandex TTS")
            else:
                raise Exception(
                    "Unexpected HTTP code from Yandex TTS ({})".format(
                        r.status_code))
        else:
            raise ValueError("API key for Yandex TTS is not defined")

    def get_tts_class(self):
        return YandexTTS
