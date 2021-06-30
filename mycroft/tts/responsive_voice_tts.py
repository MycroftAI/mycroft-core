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
from mycroft.tts.tts import TTS, TTSValidator


class ResponsiveVoice(TTS):
    def __init__(self, lang, config):
        super(ResponsiveVoice, self).__init__(
            lang, config, ResponsiveVoiceValidator(self), 'mp3',
            ssml_tags=[]
        )
        self.clear_cache()
        self.pitch = config.get("pitch", 0.5)
        self.rate = config.get("rate", 0.5)
        self.vol = config.get("vol", 1)
        if "f" not in config.get("gender", "male"):
            self.sv = "g1"
            self.vn = "rjs"
        else:
            self.vn = self.sv = ""

    def get_tts(self, sentence, wav_file):
        params = {"t": sentence, "tl": self.lang,
                  "pitch": self.pitch, "rate": self.rate,
                  "vol": self.vol, "sv": self.sv, "vn": self.vn}
        base_url = "http://responsivevoice.org/responsivevoice/getvoice.php"
        r = requests.get(base_url, params)
        with open(wav_file, "w") as f:
            f.write(r.content)
        return wav_file, None


class ResponsiveVoiceValidator(TTSValidator):
    def __init__(self, tts):
        super(ResponsiveVoiceValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO: Verify responsive voice can handle the requested language
        pass

    def validate_connection(self):
        r = requests.get("http://responsivevoice.org")
        if r.status_code == 200:
            return True
        raise AssertionError("Could not reach http://responsivevoice.org")

    def get_tts_class(self):
        return ResponsiveVoice
