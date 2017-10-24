# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

from mycroft.tts import TTSValidator
from mycroft.tts.remote_tts import RemoteTTS

__author__ = 'jarbas'


class WatsonTTS(RemoteTTS):
    PARAMS = {'accept': 'audio/wav'}

    def __init__(self, lang, config):
        super(WatsonTTS, self).__init__(lang, config,
                                        WatsonTTSValidator(self))
        if not self.url:
            self.url = "https://stream.watsonplatform.net/text-to-speech/api"
        if not self.api_path:
            self.api_path = '/v1/synthesize'
        if not self.voice:
            self.voice = "en-US_AllisonVoice"
        self.type = "wav"
        user = self.config.get("user")
        password = self.config.get("password")
        self.auth = (user, password)

    def build_request_params(self, sentence):
        params = self.PARAMS.copy()
        params['LOCALE'] = self.lang
        params['voice'] = self.voice
        params['text'] = sentence.encode('utf-8')
        return params


class WatsonTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(WatsonTTSValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        pass

    def get_tts_class(self):
        return WatsonTTS
