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

import hashlib
import requests

from .tts import TTS, TTSValidator
from .remote_tts import RemoteTTSException, RemoteTTSTimeoutException
from mycroft.configuration import Configuration
from mycroft.util.log import LOG
from mycroft.tts import cache_handler
from mycroft.util import get_cache_directory
from requests_futures.sessions import FuturesSession
from requests.exceptions import (
    ReadTimeout, ConnectionError, ConnectTimeout, HTTPError
)
from urllib import parse
from .mimic_tts import VISIMES
import math
import base64
import os
import re
import json


class MozillaTTS(TTS):
    def __init__(self, lang="en-us", config=None):
        if config is None:
            config = Configuration.get().get("tts", {}).get("mozilla", {})
        super(MozillaTTS, self).__init__(lang, config,
                                         MozillaTTSValidator(self))
        self.url = config['url']
        self.type = 'wav'

    def get_tts(self, sentence, wav_file):
        wav_name = hashlib.sha1(sentence.encode('utf-8')).hexdigest() + ".wav"
        wav_file = "/tmp/" + wav_name
        if os.path.exists(wav_file) and os.path.getsize(wav_file) > 0:
            LOG.info('local response wav found.')
        else:
            req_route = self.url + sentence
            response = requests.get(req_route)
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
        # TODO
        pass

    def get_tts_class(self):
        return MozillaTTS
