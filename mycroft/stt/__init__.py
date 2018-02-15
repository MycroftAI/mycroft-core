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
import re
import json
from abc import ABCMeta, abstractmethod
from requests import post
from speech_recognition import Recognizer

from mycroft.api import STTApi
from mycroft.configuration import Configuration
from mycroft.util.log import LOG


class STT(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        config_core = Configuration.get()
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


class GoogleJsonSTT(STT):
    __metaclass__ = ABCMeta

    def __init__(self):
        super(GoogleJsonSTT, self).__init__()
        self.json_credentials = json.dumps(self.credential.get("json"))


class BasicSTT(STT):
    __metaclass__ = ABCMeta

    def __init__(self):
        super(BasicSTT, self).__init__()
        self.username = str(self.credential.get("username"))
        self.password = str(self.credential.get("password"))


class KeySTT(STT):
    __metaclass__ = ABCMeta

    def __init__(self):
        super(KeySTT, self).__init__()
        self.id = str(self.credential.get("client_id"))
        self.key = str(self.credential.get("client_key"))


class GoogleSTT(TokenSTT):
    def __init__(self):
        super(GoogleSTT, self).__init__()

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        return self.recognizer.recognize_google(audio, self.token, self.lang)


class GoogleCloudSTT(GoogleJsonSTT):
    def __init__(self):
        super(GoogleCloudSTT, self).__init__()

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        return self.recognizer.recognize_google_cloud(audio,
                                                      self.json_credentials,
                                                      self.lang)


class WITSTT(TokenSTT):
    def __init__(self):
        super(WITSTT, self).__init__()

    def execute(self, audio, language=None):
        LOG.warning("WITSTT language should be configured at wit.ai settings.")
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
        try:
            return self.api.stt(audio.get_flac_data(convert_rate=16000),
                                self.lang, 1)[0]
        except:
            return self.api.stt(audio.get_flac_data(), self.lang, 1)[0]


class DeepSpeechServerSTT(STT):
    """
        STT interface for the deepspeech-server:
        https://github.com/MainRo/deepspeech-server
    """
    def __init__(self):
        super(DeepSpeechServerSTT, self).__init__()

    def execute(self, audio, language=None):
        language = language or self.lang
        if not language.startswith("en"):
            raise ValueError("Deepspeech is currently english only")
        response = post(self.config.get("uri"), data=audio.get_wav_data())
        return response.text


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


class BingSTT(TokenSTT):
    def __init__(self):
        super(BingSTT, self).__init__()

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        return self.recognizer.recognize_bing(audio, self.token,
                                              self.lang)


class HoundifySTT(KeySTT):
    def __init__(self):
        super(HoundifySTT, self).__init__()

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        return self.recognizer.recognize_houndify(audio, self.id, self.key)


class STTFactory(object):
    CLASSES = {
        "mycroft": MycroftSTT,
        "google": GoogleSTT,
        "google_cloud": GoogleCloudSTT,
        "wit": WITSTT,
        "ibm": IBMSTT,
        "kaldi": KaldiSTT,
        "bing": BingSTT,
        "houndify": HoundifySTT,
        "deepspeech_server": DeepSpeechServerSTT
    }

    @staticmethod
    def create():
        config = Configuration.get().get("stt", {})
        module = config.get("module", "mycroft")
        clazz = STTFactory.CLASSES.get(module)
        return clazz()
