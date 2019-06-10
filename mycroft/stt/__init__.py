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
from requests import post, put, exceptions
from speech_recognition import Recognizer
from queue import Queue
from threading import Thread

from google.cloud import speech
from google.oauth2 import service_account

from mycroft.api import STTApi
from mycroft.configuration import Configuration
from mycroft.util.log import LOG


class STT:
    __metaclass__ = ABCMeta

    def __init__(self):
        config_core = Configuration.get()
        self.lang = str(self.init_language(config_core))
        config_stt = config_core.get("stt", {})
        self.config = config_stt.get(config_stt.get("module"), {})
        self.credential = self.config.get("credential", {})
        self.recognizer = Recognizer()
        self.can_stream = False

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

    def stream_start(self):
        pass

    def stream_data(self, data):
        pass

    def stream_stop(self):
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
        # override language with module specific language selection
        self.lang = self.config.get('lang') or self.lang

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
        self.api = STTApi("stt")

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        try:
            return self.api.stt(audio.get_flac_data(convert_rate=16000),
                                self.lang, 1)[0]
        except Exception:
            return self.api.stt(audio.get_flac_data(), self.lang, 1)[0]


class MycroftDeepSpeechSTT(STT):
    """Mycroft Hosted DeepSpeech"""
    def __init__(self):
        super(MycroftDeepSpeechSTT, self).__init__()
        self.api = STTApi("deepspeech")

    def execute(self, audio, language=None):
        language = language or self.lang
        if not language.startswith("en"):
            raise ValueError("Deepspeech is currently english only")
        return self.api.stt(audio.get_wav_data(), self.lang, 1)


class DeepSpeechServerSTT(STT):
    """
        STT interface for the deepspeech-server:
        https://github.com/MainRo/deepspeech-server
        use this if you want to host DeepSpeech yourself
    """
    def __init__(self):
        super(DeepSpeechServerSTT, self).__init__()

    def execute(self, audio, language=None):
        language = language or self.lang
        if not language.startswith("en"):
            raise ValueError("Deepspeech is currently english only")
        response = post(self.config.get("uri"), data=audio.get_wav_data())
        return response.text


class StreamThread(Thread):
    def __init__(self, url, queue):
        super().__init__()
        self.url = url
        self.queue = queue
        self.response = None

    def _get_data(self):
        while True:
            d = self.queue.get()
            if d is None:
                break
            yield d
            self.queue.task_done()

    def run(self):
        self.response = post(self.url, data=self._get_data(), stream=True)


class DeepSpeechStreamServerSTT(DeepSpeechServerSTT):
    """
        Streaming STT interface for the deepspeech-server:
        https://github.com/JPEWdev/deep-dregs
        use this if you want to host DeepSpeech yourself
    """
    def __init__(self):
        super().__init__()
        self.stream = None
        self.can_stream = self.config.get('stream_uri') is not None

    def execute(self, audio, language=None):
        if self.stream is None:
            return super().execute(audio, language)
        return self.stream_stop()

    def stream_stop(self):
        if self.stream is not None:
            self.queue.put(None)
            self.stream.join()

            response = self.stream.response

            self.stream = None
            self.queue = None
            if response is None:
                return None
            return response.text
        return None

    def stream_data(self, data):
        self.queue.put(data)

    def stream_start(self, language=None):
        self.stream_stop()
        language = language or self.lang
        if not language.startswith("en"):
            raise ValueError("Deepspeech is currently english only")
        self.queue = Queue()
        self.stream = StreamThread(self.config.get("stream_uri"), self.queue)
        self.stream.start()


class GoogleStreamThread(Thread):
    def __init__(self, queue, lang, client, streaming_config):
        super().__init__()
        LOG.info('WAGNER Thread init')
        self.lang = lang
        self.client = client
        self.streaming_config = streaming_config
        self.queue = queue
        self.response = None
        self.text = ''

    def _get_data(self):
        LOG.info('WAGNER Thread get_data init')
        while True:
            d = self.queue.get()
            if d is None:
                break
            LOG.info('WAGNER Thread get_data yield d')
            yield d
            self.queue.task_done()

    def run(self):
        LOG.info('WAGNER RUN!')
        audio = self._get_data()
        req = (speech.types.StreamingRecognizeRequest(audio_content=x) for x in audio)
        responses = self.client.streaming_recognize(self.streaming_config, req)
        for res in responses:
            LOG.info('WAGNER -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=')
            LOG.info(res)
            LOG.info('WAGNER -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=')
            if res.results and res.results[0].is_final:
                self.text = res.results[0].alternatives[0].transcript


class GoogleCloudStreamingSTT(GoogleJsonSTT):
    def __init__(self):
        super(GoogleCloudStreamingSTT, self).__init__()
        # override language with module specific language selection
        self.lang = self.config.get('lang') or self.lang

        self.stream = None
        self.can_stream = True

        credentials = service_account.Credentials.from_service_account_info(
            self.credential.get('json')
        )

        self.client = speech.SpeechClient(credentials=credentials)
        recognition_config = speech.types.RecognitionConfig(
            encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=self.lang,
            model='command_and_search',
            max_alternatives=1,
        )
        self.streaming_config = speech.types.StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=True,
            single_utterance=True,
        )

    def execute(self, audio, language=None):
        #if self.stream is None:
        #    return super().execute(audio, language)
        return self.stream_stop()

    def stream_stop(self):
        LOG.info('WAGNER STOP')
        if self.stream is not None:
            self.queue.put(None)
            self.stream.join()

            text = self.stream.text

            self.stream = None
            self.queue = None
            if not text:
                return None
            return text
        return None

    def stream_data(self, data):
        LOG.info('WAGNER data! {} {}'.format(type(data), len(data)))
        self.queue.put(data)

    def stream_start(self, language=None):
        LOG.info('WAGNER START')
        self.lang = language or self.lang
        self.stream_stop()
        self.queue = Queue()
        self.stream = GoogleStreamThread(self.queue, self.lang, self.client, self.streaming_config)
        self.stream.start()


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
        except Exception:
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


class GoVivaceSTT(TokenSTT):
    def __init__(self):
        super(GoVivaceSTT, self).__init__()
        self.default_uri = "https://services.govivace.com:49149/telephony"

        if not self.lang.startswith("en") and not self.lang.startswith("es"):
            LOG.error("GoVivace STT only supports english and spanish")
            raise NotImplementedError

    def execute(self, audio, language=None):
        url = self.config.get("uri", self.default_uri) + "?key=" + \
              self.token + "&action=find&format=8K_PCM16&validation_string="
        response = put(url,
                       data=audio.get_wav_data(convert_rate=8000))
        return self.get_response(response)

    def get_response(self, response):
        return response.json()["result"]["hypotheses"][0]["transcript"]


class STTFactory:
    CLASSES = {
        "mycroft": MycroftSTT,
        "google": GoogleSTT,
        "google_cloud": GoogleCloudSTT,
        "google_cloud_streaming": GoogleCloudStreamingSTT,
        "wit": WITSTT,
        "ibm": IBMSTT,
        "kaldi": KaldiSTT,
        "bing": BingSTT,
        "govivace": GoVivaceSTT,
        "houndify": HoundifySTT,
        "deepspeech_server": DeepSpeechServerSTT,
        "deepspeech_stream_server": DeepSpeechStreamServerSTT,
        "mycroft_deepspeech": MycroftDeepSpeechSTT
    }

    @staticmethod
    def create():
        config = Configuration.get().get("stt", {})
        module = config.get("module", "mycroft")
        clazz = STTFactory.CLASSES.get(module)
        return clazz()
