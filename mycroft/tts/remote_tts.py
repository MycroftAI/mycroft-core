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


import abc

import re
from requests_futures.sessions import FuturesSession

from mycroft.tts import TTS
from mycroft.util import remove_last_slash, play_wav
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class RemoteTTS(TTS):
    """
    Abstract class for a Remote TTS engine implementation.

    It provides a common logic to perform multiple requests by splitting the
    whole sentence into small ones.
    """

    def __init__(self, lang, voice, url, api_path, validator):
        super(RemoteTTS, self).__init__(lang, voice, validator)
        self.api_path = api_path
        self.url = remove_last_slash(url)
        self.session = FuturesSession()

    def execute(self, sentence):
        phrases = self.__get_phrases(sentence)

        if len(phrases) > 0:
            for req in self.__requests(phrases):
                try:
                    self.__play(req)
                except Exception, e:
                    LOGGER.error(e.message)

    @staticmethod
    def __get_phrases(sentence):
        phrases = re.split('\.+[\s+|\n]', sentence)
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
            timeout=10, verify=False)

    @abc.abstractmethod
    def build_request_params(self, sentence):
        pass

    def __play(self, req):
        resp = req.result()
        if resp.status_code == 200:
            self.__save(resp.content)
            play_wav(self.filename).communicate()
        else:
            LOGGER.error(
                '%s Http Error: %s for url: %s' %
                (resp.status_code, resp.reason, resp.url))

    def __save(self, data):
        with open(self.filename, 'wb') as f:
            f.write(data)
