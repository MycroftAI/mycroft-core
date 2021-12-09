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
import abc
import re
from requests_futures.sessions import FuturesSession

from .tts import TTS
from mycroft.util import play_wav
from mycroft.util.log import LOG


class RemoteTTSException(Exception):
    pass


class RemoteTTSTimeoutException(RemoteTTSException):
    pass


class RemoteTTS(TTS):
    """
    Abstract class for a Remote TTS engine implementation.

    It provides a common logic to perform multiple requests by splitting the
    whole sentence into small ones.
    """

    def __init__(self, lang, config, url, api_path, validator):
        super(RemoteTTS, self).__init__(lang, config, validator)
        self.api_path = api_path
        self.auth = None
        self.url = config.get('url', url).rstrip('/')
        self.session = FuturesSession()

    def execute(self, sentence, ident=None, listen=False):
        phrases = self.__get_phrases(sentence)

        if len(phrases) > 0:
            for req in self.__requests(phrases):
                try:
                    self.begin_audio()
                    self.__play(req)
                except Exception as e:
                    LOG.error(e.message)
                finally:
                    self.end_audio(listen)

    @staticmethod
    def __get_phrases(sentence):
        phrases = re.split(r'\.+[\s+|\n]', sentence)
        phrases = [p.replace('\n', '').strip() for p in phrases]
        phrases = [p for p in phrases if len(p) > 0]
        return phrases

    def __requests(self, phrases):
        reqs = []
        for p in phrases:
            reqs.append(self.__request(p))
        return reqs

    def __request(self, p):
        return self.session.get(
            self.url + self.api_path, params=self.build_request_params(p),
            timeout=10, verify=False, auth=self.auth)

    @abc.abstractmethod
    def build_request_params(self, sentence):
        pass

    def __play(self, req):
        resp = req.result()
        if resp.status_code == 200:
            self.__save(resp.content)
            play_wav(self.filename).communicate()
        else:
            LOG.error(
                '%s Http Error: %s for url: %s' %
                (resp.status_code, resp.reason, resp.url))

    def __save(self, data):
        with open(self.filename, 'wb') as f:
            f.write(data)
