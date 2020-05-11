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


class ESpeak(TTS):
    """TTS module for generating speech using ESpeak."""
    def __init__(self, lang, config):
        super(ESpeak, self).__init__(lang, config, ESpeakValidator(self))

    def get_tts(self, sentence, wav_file):
        """Generate WAV from sentence, phonemes aren't supported.

        Arguments:
            sentence (str): sentence to generate audio for
            wav_file (str): output file

        Returns:
            tuple ((str) file location, None)
        """
        subprocess.call(['espeak', '-v', self.lang + '+' + self.voice,
                         '-w', wav_file, sentence])
        return wav_file, None


class ESpeakValidator(TTSValidator):
    def __init__(self, tts):
        super(ESpeakValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            subprocess.call(['espeak', '--version'])
        except Exception:
            raise Exception('ESpeak is not installed. Please install it on '
                            'your system and restart Mycroft.')

    def get_tts_class(self):
        return ESpeak
