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
import subprocess

from mycroft.tts.tts import TTS, TTSValidator


class Festival(TTS):
    def __init__(self, lang, config):
        super(Festival, self).__init__(lang, config, FestivalValidator(self))

    def execute(self, sentence, ident=None, listen=False):

        encoding = self.config.get('encoding', 'utf8')
        lang = self.config.get('lang', self.lang)

        text = subprocess.Popen(('echo', sentence), stdout=subprocess.PIPE)

        if encoding != 'utf8':
            convert_cmd = ('iconv', '-f', 'utf8', '-t', encoding)
            converted_text = subprocess.Popen(convert_cmd,
                                              stdin=text.stdout,
                                              stdout=subprocess.PIPE)
            text.wait()
            text = converted_text

        tts_cmd = ('festival', '--tts', '--language', lang)

        self.begin_audio()
        subprocess.call(tts_cmd, stdin=text.stdout)
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
                'Festival is missing. Run: sudo apt-get install festival')

    def get_tts_class(self):
        return Festival
