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

from .tts import TTS, TTSValidator


class Festival(TTS):
    def __init__(self, lang, config):
        super(Festival, self).__init__(lang, config, FestivalValidator(self))

    def execute(self, sentence, ident=None, listen=False):

        toencoding = self.config.get('toencoding')

        if toencoding != 'utf8':
            cmd = "echo \"" + sentence + "\" | iconv -f utf8 -t " + toencoding + " | festival --tts --language " + self.lang
        else:
            cmd = "echo \"" + sentence + "\" | festival --tts --language " + self.lang

        self.begin_audio()
        subprocess.call(cmd, shell=True)
        self.end_audio(listen)


class FestivalValidator(TTSValidator):
    def __init__(self, tts):
        super(FestivalValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            subprocess.call(['festival', '--version'])
        except Exception:
            raise Exception(
                'Festival is not installed. Run: sudo apt-get install festival')

    def get_tts_class(self):
        return Festival
