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


class Say(TTS):
    def __init__(self, lang, config):
        super(Say, self).__init__(lang, config, SayValidator(self))

    def execute(self, sentence, ident=None):
        self.begin_audio()
        subprocess.call(
            ['say', self.lang, sentence])
        self.end_audio()


class SayValidator(TTSValidator):
    def __init__(self, tts):
        super(SayValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            subprocess.call(['say', 'hello'])
        except:
            raise Exception('Say is not installed')

    def get_tts_class(self):
        return Say
