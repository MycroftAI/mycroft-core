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

"""Baidu tts"""

from mycroft.util.log import LOG

from .tts import TTS, TTSValidator
from aip import AipSpeech


# todo: mycroft-core-zh, improvement is needed.
class BaiduTTS(TTS):
    def __init__(self, lang, config):
        super(BaiduTTS, self).__init__(lang, config, BaiduValidator(self), 'mp3')
        self.client = AipSpeech(config['appid'], config['credential']['api_key'], config['credential']['secret_key'])

    def get_tts(self, sentence, wav_file):
        response = self.client.synthesis(sentence, 'zh', 1, {'per': self.voice})
        LOG.info('[Flow Learning] in mycroft.tts.baidu_tts.py.BaiduTTS.get_tts, after calling TTS api, wav_file will ==' + str(wav_file))
        LOG.debug('response is ' + str(response))
        if not isinstance(response, dict):
            LOG.info('[Flow Learning] get response from Baidu tts')
            with open(wav_file, 'wb') as f:
                f.write(response)
            return (wav_file, None)  # No phonemes
        else:
            LOG.error('Fail to call Baidu tts! error = ' + str(response))


class BaiduValidator(TTSValidator):
    """Do no tests."""
    def __init__(self, tts):
        super().__init__(tts)

    def validate_lang(self):
        pass

    def validate_connection(self):
        pass

    def get_tts_class(self):
        return BaiduTTS
