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


#imports for json handling, requests and string formatting for KaldiSTT
import json
import requests
import re

__author__ = "jdorleans"

LOG = getLogger("STT")


class STT(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        config_core = ConfigurationManager.get()
        self.lang = str(self.init_language(config_core))
        self.config = config_core.get("stt")
        self.credential = self.config.get(self.config.get("module"), {})
        self.recognizer = Recognizer()

    @staticmethod
    def init_language(config_core):
        langs = config_core.get("lang", "en-US").split("-")
        return langs[0].lower() + "-" + langs[1].upper()

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
        language = language or self.lang
        return self.recognizer.recognize_google(audio, self.token, language)


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
        language = language or self.lang
        return self.recognizer.recognize_ibm(audio, self.username,
                                             self.password, language)


class MycroftSTT(STT):
    def __init__(self):
        super(MycroftSTT, self).__init__()
        self.api = STTApi()

    def execute(self, audio, language=None):
        language = language or self.lang
        return self.api.stt(audio.get_flac_data(), language, 1)[0]

#KaldiSTT added. Unsure which class to use BasicSTT, STT or TokenSTT
#The problem is that with "module": "kaldi" in the config file, mycroft still falls back to MycroftSTT. "update" in config has to be set to false

class KaldiSTT(STT):
    def __init__(self):
        super(KaldiSTT, self).__init__()
        #self.api = STTApi() necessary?

    def execute(self, audio, language=None):
        language = language or self.lang
        
        port_kaldi = 8081 #default port        
        config = ConfigurationManager.get().get("stt", {})
        port_kaldi = config.get("port")
        print("Port for localhost Kaldi Server:", port_kaldi)
        
        #the kaldigstserver has to run at localhost on the defined port in the config file under stt "port": xxxx
        kaldi_server_response = requests.post("http://localhost:%s/client/dynamic/recognize" % port_kaldi, data=audio.get_wav_data())        
        kaldi_json = json.loads(kaldi_server_response.text)
        hypotheses = kaldi_json["hypotheses"]
        
        #re.sub... deletes all [noise] inserts made by kaldi        
        return re.sub(r'\s*\[noise\]\s*', '', hypotheses[0]["utterance"])


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
