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

from mycroft.tts.tts import TTS, TTSValidator
from mycroft.configuration import Configuration


class BingTTS(TTS):
    def __init__(self, lang, config):
        super(BingTTS, self).__init__(lang, config, BingTTSValidator(self))
        self.type = 'wav'
        from bingtts import Translator
        self.config = Configuration.get().get("tts", {}).get("bing", {})
        api = self.config.get("api_key")
        self.bing = Translator(api)
        self.gender = self.config.get("gender", "Male")
        self.format = self.config.get("format", "riff-16khz-16bit-mono-pcm")

    def get_tts(self, sentence, wav_file):
        output = self.bing.speak(sentence, self.lang, self.gender,
                                 self.format)
        with open(wav_file, "w") as f:
            f.write(output)
        return (wav_file, None)  # No phonemes


class BingTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(BingTTSValidator, self).__init__(tts)

    def validate_dependencies(self):
        try:
            from bingtts import Translator
        except ImportError:
            raise Exception(
                'BingTTS dependencies not installed, please run pip install '
                'git+https://github.com/westparkcom/Python-Bing-TTS.git ')

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        # TODO
        pass

    def get_tts_class(self):
        return BingTTS
