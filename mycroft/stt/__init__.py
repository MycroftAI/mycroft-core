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
from abc import ABCMeta, abstractmethod

from speech_recognition import Recognizer

from mycroft.api import STTApi
from mycroft.configuration import ConfigurationManager
from mycroft.util.log import getLogger

import re

from requests import post

__author__ = "jdorleans"

LOG = getLogger("STT")


class STT(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        config_core = ConfigurationManager.get()
        self.lang = str(self.init_language(config_core))
        config_stt = config_core.get("stt", {})
        self.config = config_stt.get(config_stt.get("module"), {})
        self.credential = self.config.get("credential", {})
        self.recognizer = Recognizer()

    @staticmethod
    def init_language(config_core):
        lang = config_core.get("lang", "en-US")
        langs = lang.split("-")
        if len(langs) == 2:
            return langs[0].lower() + "-" + langs[1].upper()
        return lang

    @abstractmethod
    def execute(self, audio, language=None):
        pass


class TokenSTT(STT):
    __metaclass__ = ABCMeta

    def __init__(self):
        super(TokenSTT, self).__init__()
        self.token = str(self.credential.get("token"))


class BasicSTT(STT):
    __metaclass__ = ABCMeta

    def __init__(self):
        super(BasicSTT, self).__init__()
        self.username = str(self.credential.get("username"))
        self.password = str(self.credential.get("password"))


class GoogleSTT(TokenSTT):
    def __init__(self):
        super(GoogleSTT, self).__init__()

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        return self.recognizer.recognize_google(audio, self.token, self.lang)


class WITSTT(TokenSTT):
    def __init__(self):
        super(WITSTT, self).__init__()

    def execute(self, audio, language=None):
        LOG.warn("WITSTT language should be configured at wit.ai settings.")
        return self.recognizer.recognize_wit(audio, self.token)


class IBMSTT(BasicSTT):
    def __init__(self):
        super(IBMSTT, self).__init__()

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        return self.recognizer.recognize_ibm(audio, self.username,
                                             self.password, self.lang)


class MycroftSTT(STT):
    def __init__(self):
        super(MycroftSTT, self).__init__()
        self.api = STTApi()

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        return self.api.stt(audio.get_flac_data(), self.lang, 1)[0]


class KaldiSTT(STT):
    def __init__(self):
        super(KaldiSTT, self).__init__()

    def execute(self, audio, language=None):
        language = language or self.lang
        response = post(self.config.get("uri"), data=audio.get_wav_data())
        return self.get_response(response)

    def get_response(self, response):
        try:
            hypotheses = response.json()["hypotheses"]
            return re.sub(r'\s*\[noise\]\s*', '', hypotheses[0]["utterance"])
        except:
            return None


class STTFactory(object):
    CLASSES = {
        "mycroft": MycroftSTT,
        "google": GoogleSTT,
        "wit": WITSTT,
        "ibm": IBMSTT,
        "kaldi": KaldiSTT
    }

    @staticmethod
    def create():
        config = ConfigurationManager.get().get("stt", {})
        module = config.get("module", "mycroft")
        clazz = STTFactory.CLASSES.get(module)
        return clazz()
