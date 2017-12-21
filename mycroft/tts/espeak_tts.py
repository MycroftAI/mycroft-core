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
import subprocess

from mycroft.tts import TTS, TTSValidator


class ESpeak(TTS):
    def __init__(self, lang, voice):
        super(ESpeak, self).__init__(lang, voice, ESpeakValidator(self))

    def execute(self, sentence, ident=None):
        self.begin_audio()
        subprocess.call(
            ['espeak', '-v', self.lang + '+' + self.voice, sentence])
        self.end_audio()


class ESpeakValidator(TTSValidator):
    def __init__(self, tts):
        super(ESpeakValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            subprocess.call(['espeak', '--version'])
        except:
            raise Exception(
                'ESpeak is not installed. Run: sudo apt-get install espeak')

    def get_tts_class(self):
        return ESpeak
