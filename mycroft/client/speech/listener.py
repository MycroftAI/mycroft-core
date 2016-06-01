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


import threading
import time
from Queue import Queue

import pyee
import speech_recognition as sr

from mycroft.client.speech.local_recognizer import LocalRecognizer
from mycroft.client.speech.mic import MutableMicrophone, Recognizer
from mycroft.client.speech.recognizer_wrapper import \
    RemoteRecognizerWrapperFactory
from mycroft.client.speech.word_extractor import WordExtractor
from mycroft.configuration.config import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.metrics import MetricsAggregator, Stopwatch
from mycroft.session import SessionManager
from mycroft.util import CerberusAccessDenied
from mycroft.util.log import getLogger

logger = getLogger(__name__)

core_config = ConfigurationManager.get_config().get('core')
speech_config = ConfigurationManager.get_config().get('speech_client')


class AudioProducer(threading.Thread):
    """
    AudioProducer
    given a mic and a recognizer implementation, continuously listens to the
    mic for potential speech chunks and pushes them onto the queue.
    """

    def __init__(self, state, queue, mic, recognizer, emitter):
        threading.Thread.__init__(self)
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
                    self.emitter.emit("recognizer_loop:listening")
                    audio = self.recognizer.listen(source)
                    self.queue.put(audio)
                except IOError, ex:
                    # NOTE: Audio stack on raspi is slightly different, throws
                    # IOError every other listen, almost like it can't handle
                    # buffering audio between listen loops.
                    # The internet was not helpful.
                    # http://stackoverflow.com/questions/10733903/pyaudio-input-overflowed
                    self.emitter.emit("recognizer_loop:ioerror", ex)


class AudioConsumer(threading.Thread):
    """
    AudioConsumer
    Consumes AudioData chunks off the queue
    """

    # In seconds, the minimum audio size to be sent to remote STT
    MIN_AUDIO_SIZE = 1.0

    def __init__(self, state, queue, emitter, wakeup_recognizer,
                 mycroft_recognizer, remote_recognizer):
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = queue
        self.state = state
        self.emitter = emitter
        self.wakeup_recognizer = wakeup_recognizer
        self.mycroft_recognizer = mycroft_recognizer
        self.remote_recognizer = remote_recognizer
        self.metrics = MetricsAggregator()

    def run(self):
        while self.state.running:
            self.read_audio()

    @staticmethod
    def _audio_length(audio):
        return float(len(audio.frame_data)) / (
            audio.sample_rate * audio.sample_width)

    def read_audio(self):
        timer = Stopwatch()
        audio = self.queue.get()
        self.metrics.timer("mycroft.recognizer.audio.length_s",
                           self._audio_length(audio))
        self.queue.task_done()
        timer.start()

        if self.state.sleeping:
            self.process_wake_up(audio)
        elif self.state.skip_wakeword:
            self.process_skip_wake_word(audio)
        else:
            self.process_wake_word(audio, timer)

        self.metrics.flush()

    def process_wake_up(self, audio):
        if self.wakeup_recognizer.is_recognized(audio.frame_data,
                                                self.metrics):
            SessionManager.touch()
            self.state.sleeping = False
            self.__speak("I'm awake.")  # TODO: Localization
            self.metrics.increment("mycroft.wakeup")

    def process_wake_word(self, audio, timer):
        hyp = self.mycroft_recognizer.transcribe(audio.frame_data,
                                                 self.metrics)

        if self.mycroft_recognizer.contains(hyp):
            extractor = WordExtractor(audio, self.mycroft_recognizer,
                                      self.metrics)
            timer.lap()
            extractor.calculate_range()
            self.metrics.timer("mycroft.recognizer.extractor.time_s",
                               timer.lap())
            audio_before = extractor.get_audio_data_before()
            self.metrics.timer("mycroft.recognizer.audio_extracted.length_s",
                               self._audio_length(audio_before))
            audio_after = extractor.get_audio_data_after()
            self.metrics.timer("mycroft.recognizer.audio_extracted.length_s",
                               self._audio_length(audio_after))

            SessionManager.touch()
            payload = {
                'utterance': hyp.hypstr,
                'session': SessionManager.get().session_id,
                'pos_begin': extractor.begin,
                'pos_end': extractor.end
            }
            self.emitter.emit("recognizer_loop:wakeword", payload)

            try:
                self.transcribe([audio_before, audio_after])
            except sr.UnknownValueError:
                self.__speak("Go ahead")
                self.state.skip_wakeword = True
                self.metrics.increment("mycroft.wakeword")

    def process_skip_wake_word(self, audio):
        SessionManager.touch()
        try:
            self.transcribe([audio])
        except sr.UnknownValueError:
            logger.warn("Speech Recognition could not understand audio")
            self.__speak("Sorry, I didn't catch that.")
            self.metrics.increment("mycroft.recognizer.error")
        self.state.skip_wakeword = False

    def __speak(self, utterance):
        """
        Speak commands should be asynchronous to avoid filling up the portaudio
        buffer.
        :param utterance:
        :return:
        """

        def target():
            payload = {
                'utterance': utterance,
                'session': SessionManager.get().session_id
            }
            self.emitter.emit("speak", Message("speak", metadata=payload))

        threading.Thread(target=target).start()

    def _create_remote_stt_runnable(self, audio, utterances):
        def runnable():
            try:
                text = self.remote_recognizer.transcribe(
                        audio, metrics=self.metrics).lower()
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                logger.error(
                        "Could not request results from Speech Recognition "
                        "service; {0}".format(e))
            except CerberusAccessDenied as e:
                logger.error("AccessDenied from Cerberus proxy.")
                self.__speak(
                        "Your device is not registered yet. To start pairing, "
                        "login at cerberus.mycroft.ai")
                utterances.append("pair my device")
            except Exception as e:
                logger.error("Unexpected exception: {0}".format(e))
            else:
                logger.debug("STT: " + text)
                if text.strip() != '':
                    utterances.append(text)

        return runnable

    def transcribe(self, audio_segments):
        utterances = []
        threads = []
        for audio in audio_segments:
            if self._audio_length(audio) < self.MIN_AUDIO_SIZE:
                logger.debug("Audio too short to send to STT")
                continue

            target = self._create_remote_stt_runnable(audio, utterances)
            t = threading.Thread(target=target)
            t.start()
            threads.append(t)

        for thread in threads:
            thread.join()
        if len(utterances) > 0:
            payload = {
                'utterances': utterances,
                'session': SessionManager.get().session_id
            }
            self.emitter.emit("recognizer_loop:utterance", payload)
            self.metrics.attr('utterances', utterances)
        else:
            raise sr.UnknownValueError


class RecognizerLoopState(object):
    def __init__(self):
        self.running = False
        self.sleeping = False
        self.skip_wakeword = False


class RecognizerLoop(pyee.EventEmitter):
    def __init__(self, channels=int(speech_config.get('channels')),
                 sample_rate=int(speech_config.get('sample_rate')),
                 device_index=None,
                 lang=core_config.get('lang')):
        pyee.EventEmitter.__init__(self)
        self.microphone = MutableMicrophone(sample_rate=sample_rate,
                                            device_index=device_index)

        # FIXME - channels are not been used
        self.microphone.CHANNELS = channels
        self.mycroft_recognizer = LocalRecognizer(sample_rate, lang)
        # TODO - localization
        self.wakeup_recognizer = LocalRecognizer(sample_rate, lang, "wake up")
        self.remote_recognizer = Recognizer()
        self.state = RecognizerLoopState()

    def start_async(self):
        self.state.running = True
        queue = Queue()
        AudioProducer(self.state,
                      queue,
                      self.microphone,
                      self.remote_recognizer,
                      self).start()
        AudioConsumer(self.state,
                      queue,
                      self,
                      self.wakeup_recognizer,
                      self.mycroft_recognizer,
                      RemoteRecognizerWrapperFactory.wrap_recognizer(
                              self.remote_recognizer)).start()

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
                logger.error(e)
                self.stop()
