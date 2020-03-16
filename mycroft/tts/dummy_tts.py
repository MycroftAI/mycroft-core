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

"""A Dummy TTS without any audio output."""

from mycroft.util.log import LOG

from .tts import TTS, TTSValidator


class DummyTTS(TTS):
    def __init__(self, lang, config):
        super().__init__(lang, config, DummyValidator(self), 'wav')

    def execute(self, sentence, ident=None, listen=False):
        """Don't do anything, return nothing."""
        LOG.info('Mycroft: {}'.format(sentence))
        return None


class DummyValidator(TTSValidator):
    """Do no tests."""
    def __init__(self, tts):
        super().__init__(tts)

    def validate_lang(self):
        pass

    def validate_connection(self):
        pass

    def get_tts_class(self):
        return DummyTTS
