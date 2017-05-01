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


import time
from Queue import Queue
from threading import Thread

import speech_recognition as sr
from pyee import EventEmitter
from requests import HTTPError
from requests.exceptions import ConnectionError

from mycroft.client.speech.local_recognizer import LocalRecognizer
from mycroft.client.speech.mic import MutableMicrophone, ResponsiveRecognizer
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.metrics import MetricsAggregator
from mycroft.session import SessionManager
from mycroft.stt import STTFactory
from mycroft.util import connected
from mycroft.util.log import getLogger

LOG = getLogger(__name__)


class AudioProducer(Thread):
    """
    AudioProducer
    given a mic and a recognizer implementation, continuously listens to the
    mic for potential speech chunks and pushes them onto the queue.
    """

    def __init__(self, state, queue, mic, recognizer, emitter):
        super(AudioProducer, self).__init__()
        self.daemon = True
        self.state = state
        self.queue = queue
        self.mic = mic
        self.recognizer = recognizer
        self.emitter = emitter

    def run(self):
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while self.state.running:
                try:
                    audio = self.recognizer.listen(source, self.emitter)
                    self.queue.put(audio)
                except IOError, ex:
                    # NOTE: Audio stack on raspi is slightly different, throws
                    # IOError every other listen, almost like it can't handle
                    # buffering audio between listen loops.
                    # The internet was not helpful.
                    # http://stackoverflow.com/questions/10733903/pyaudio-input-overflowed
                    self.emitter.emit("recognizer_loop:ioerror", ex)


class AudioConsumer(Thread):
    """
    AudioConsumer
    Consumes AudioData chunks off the queue
    """

    # In seconds, the minimum audio size to be sent to remote STT
    MIN_AUDIO_SIZE = 0.5

    def __init__(self, state, queue, emitter, stt,
                 wakeup_recognizer, mycroft_recognizer):
        super(AudioConsumer, self).__init__()
        self.daemon = True
        self.queue = queue
        self.state = state
        self.emitter = emitter
        self.stt = stt
        self.wakeup_recognizer = wakeup_recognizer
        self.mycroft_recognizer = mycroft_recognizer
        self.metrics = MetricsAggregator()

    def run(self):
        while self.state.running:
            self.read()

    def read(self):
        audio = self.queue.get()

        if self.state.sleeping:
            self.wake_up(audio)
        else:
            self.process(audio)

    # TODO: Localization
    def wake_up(self, audio):
        if self.wakeup_recognizer.is_recognized(audio.frame_data,
                                                self.metrics):
            SessionManager.touch()
            self.state.sleeping = False
            self.__speak("I'm awake.")
            self.metrics.increment("mycroft.wakeup")

    @staticmethod
    def _audio_length(audio):
        return float(len(audio.frame_data)) / (
            audio.sample_rate * audio.sample_width)

    # TODO: Localization
    def process(self, audio):
        SessionManager.touch()
        payload = {
            'utterance': self.mycroft_recognizer.key_phrase,
            'session': SessionManager.get().session_id,
        }
        self.emitter.emit("recognizer_loop:wakeword", payload)

        if self._audio_length(audio) < self.MIN_AUDIO_SIZE:
            LOG.warn("Audio too short to be processed")
        else:
            self.transcribe(audio)

    def transcribe(self, audio):
        text = None
        try:
            # Invoke the STT engine on the audio clip
            text = self.stt.execute(audio).lower().strip()
            LOG.debug("STT: " + text)
        except sr.RequestError as e:
            LOG.error("Could not request Speech Recognition {0}".format(e))
        except ConnectionError as e:
            LOG.error("Connection Error: {0}".format(e))
            self.__speak("Mycroft seems not to be connected to the Internet")
        except HTTPError as e:
            if e.response.status_code == 401:
                text = "pair my device"
                LOG.warn("Access Denied at mycroft.ai")
        except Exception as e:
            LOG.error(e)
            LOG.error("Speech Recognition could not understand audio")
            self.__speak("Sorry, I didn't catch that")
        if text:
            # STT succeeded, send the transcribed speech on for processing
            payload = {
                'utterances': [text],
                'lang': self.stt.lang,
                'session': SessionManager.get().session_id
            }
            self.emitter.emit("recognizer_loop:utterance", payload)
            self.metrics.attr('utterances', [text])

    def __speak(self, utterance):
        payload = {
            'utterance': utterance,
            'session': SessionManager.get().session_id
        }
        self.emitter.emit("speak", Message("speak", payload))


class RecognizerLoopState(object):
    def __init__(self):
        self.running = False
        self.sleeping = False


class RecognizerLoop(EventEmitter):
    def __init__(self):
        super(RecognizerLoop, self).__init__()
        config = ConfigurationManager.get()
        lang = config.get('lang')
        self.config = config.get('listener')
        rate = self.config.get('sample_rate')
        device_index = self.config.get('device_index')

        self.microphone = MutableMicrophone(device_index, rate)
        # FIXME - channels are not been used
        self.microphone.CHANNELS = self.config.get('channels')
        self.mycroft_recognizer = self.create_mycroft_recognizer(rate, lang)
        # TODO - localization
        self.wakeup_recognizer = self.create_wakeup_recognizer(rate, lang)
        self.remote_recognizer = ResponsiveRecognizer(self.mycroft_recognizer)
        self.state = RecognizerLoopState()

    def create_mycroft_recognizer(self, rate, lang):
        # Create a local recognizer to hear the wakeup word, e.g. 'Hey Mycroft'
        wake_word = self.config.get('wake_word')
        phonemes = self.config.get('phonemes')
        threshold = self.config.get('threshold')
        return LocalRecognizer(wake_word, phonemes, threshold, rate, lang)

    def create_wakeup_recognizer(self, rate, lang):
        wake_word = self.config.get('standup_word', "wake up")
        phonemes = self.config.get('standup_phonemes', "W EY K . AH P")
        threshold = self.config.get('standup_threshold', 1e-10)
        return LocalRecognizer(wake_word, phonemes, threshold, rate, lang)

    def start_async(self):
        self.state.running = True
        queue = Queue()
        AudioProducer(self.state, queue, self.microphone,
                      self.remote_recognizer, self).start()
        AudioConsumer(self.state, queue, self, STTFactory.create(),
                      self.wakeup_recognizer, self.mycroft_recognizer).start()

    def stop(self):
        self.state.running = False

    def mute(self):
        if self.microphone:
            self.microphone.mute()

    def unmute(self):
        if self.microphone:
            self.microphone.unmute()

    def sleep(self):
        self.state.sleeping = True

    def awaken(self):
        self.state.sleeping = False

    def run(self):
        self.start_async()
        while self.state.running:
            try:
                time.sleep(1)
            except KeyboardInterrupt as e:
                LOG.error(e)
                self.stop()
