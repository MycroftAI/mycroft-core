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

from mycroft.tts.tts import TTS, TTSValidator
from mycroft.configuration import Configuration


class MozillaTTS(TTS):
    def __init__(self, lang="en-us", config=None):
        if config is None:
            self.config = Configuration.get().get("tts", {}).get("mozilla", {})
        else:
            self.config = config
        super(MozillaTTS, self).__init__(lang, self.config,
                                         MozillaTTSValidator(self))
        self.url = self.config['url'] + "/api/tts"
        self.type = 'wav'

    def get_tts(self, sentence, wav_file):
        response = requests.get(self.url, params={'text': sentence})
        with open(wav_file, 'wb') as f:
            f.write(response.content)
        return (wav_file, None)  # No phonemes


class MozillaTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(MozillaTTSValidator, self).__init__(tts)

    def validate_dependencies(self):
        pass

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        url = self.tts.config['url']
        response = requests.get(url)
        if not response.status_code == 200:
            raise ConnectionRefusedError

    def get_tts_class(self):
        return MozillaTTS
