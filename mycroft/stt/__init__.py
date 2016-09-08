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

__author__ = "jdorleans"

LOG = getLogger("STT")


class STT(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self.config = ConfigurationManager.get().get("stt")
        self.recognizer = Recognizer()

    @abstractmethod
    def execute(self, audio, lang):
        pass


class STTToken(STT):
    __metaclass__ = ABCMeta

    def __init__(self):
        super(STTToken, self).__init__()
        self.token = self.config.get("credential").get("token")


class STTBasic(STT):
    __metaclass__ = ABCMeta

    def __init__(self):
        super(STTBasic, self).__init__()
        credential = self.config.get("credential")
        self.username = credential.get("username")
        self.password = credential.get("password")


class GoogleSTT(STTToken):
    def __init__(self):
        super(GoogleSTT, self).__init__()

    def execute(self, audio, language):
        return self.recognizer.recognize_google(audio, self.token, language)


class WITSTT(STTToken):
    def __init__(self):
        super(WITSTT, self).__init__()

    def execute(self, audio, language):
        LOG.warn("English is the only language supported by WIT STT.")
        return self.recognizer.recognize_wit(audio, self.token)


class IBMSTT(STTBasic):
    def __init__(self):
        super(IBMSTT, self).__init__()

    def execute(self, audio, language):
        return self.recognizer.recognize_ibm(audio, self.username,
                                             self.password, language)


class MycroftSTT(STT):
    def __init__(self):
        super(MycroftSTT, self).__init__()
        self.api = STTApi()

    def execute(self, audio, language):
        return self.api.stt(audio, language)


class STTFactory(object):
    CLASSES = {
        "mycroft": MycroftSTT,
        "google": GoogleSTT,
        "wit": WITSTT,
        "ibm": IBMSTT
    }

    @staticmethod
    def create():
        config = ConfigurationManager.get().get("stt", {})
        module = config.get("module", "mycroft")
        clazz = STTFactory.CLASSES.get(module)
        return clazz()
