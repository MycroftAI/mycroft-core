# Copyright 2020 Mycroft AI Inc.
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


class DilmancTTS(TTS):
    def __init__(self, lang="az-az", config=None):
        if config is None:
            self.config = Configuration.get().get("tts", {}).get("dilmanc", {})
        else:
            self.config = config
        super(DilmancTTS, self).__init__(lang, self.config,
                                         DilmancTTSValidator(self))
        self.session = requests.Session()
        self.url = self.config['url']
        self.id = None
        self.code = None
        self.speed = float(self.config['speed'])
        self.audio_ext = "mp3"
        self.get_id_and_code()

    def get_id_and_code(self):
        result = self.session.get(self.url)
        text = result.text
        idx = text.find("action")
        idx = text.find("id", idx)
        idx2 = text.find("&", idx)
        self.id = text[idx + 3:idx2]
        idx = text.find("id", idx2)
        self.code = text[idx2 + 6:idx - 2]

    def download_audio(self, url, mp3_file):
        with self.session.get(url, stream=True) as r:
            r.raise_for_status()
            with open(mp3_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def get_tts(self, sentence, mp3_file):
        if not self.id or not self.code:
            self.get_id_and_code
        data = "from={}&tts_submit=%C2%A0%C2%A0Listen&speechspeed={:.2f}"\
            .format(sentence, self.speed).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded",
                   "Referer": "http://dilmanc.az/en/text-to-speech"}
        result = self.session.post(
            url=self.url + "?id={}&code={}".format(self.id, self.code),
            data=data, headers=headers)
        text = result.text
        idx = text.find("<audio")
        idx = text.find("src", idx)
        idx2 = text.find("type", idx)
        mp3_file_url = text[idx+5:idx2-2]
        self.download_audio(mp3_file_url, mp3_file)
        return mp3_file, None  # No phonemes


class DilmancTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(DilmancTTSValidator, self).__init__(tts)

    def validate_dependencies(self):
        pass

    def validate_lang(self):
        config = Configuration.get().get("tts", {}).get("dilmanc", {})
        lang = config.get("lang", "")
        if lang == "az-az":
            return True
        raise ValueError("Unsupported language for Dilmanc TTS")

    def validate_connection(self):
        config = Configuration.get().get("tts", {}).get("dilmanc", {})
        url = config.get("url")
        response = requests.get(url)
        if not response.status_code == 200:
            raise ConnectionRefusedError

    def get_tts_class(self):
        return DilmancTTS
