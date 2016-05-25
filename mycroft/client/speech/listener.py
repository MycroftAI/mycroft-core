"""
Copyright 2016 Mycroft AI, Inc.

This file is part of Mycroft Core.

Mycroft Core is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Mycroft Core is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.
"""

import threading
import time
from Queue import Queue

import os
import pyee
import speech_recognition as sr
from speech_recognition import AudioData

from mycroft.client.speech import wakeword_recognizer
from mycroft.client.speech.mic import MutableMicrophone, Recognizer
from mycroft.client.speech.recognizer_wrapper import (
    RemoteRecognizerWrapperFactory
)
from mycroft.configuration.config import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.metrics import MetricsAggregator, Stopwatch
from mycroft.session import SessionManager
from mycroft.util import read_stripped_lines, CerberusAccessDenied
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


class WakewordExtractor:

    MAX_ERROR_SECONDS = 0.02
    TRIM_SECONDS = 0.1
    # The seconds the safe end position is pushed back to ensure pocketsphinx
    # is consistent
    PUSH_BACK_SECONDS = 0.2
    # The seconds of silence padded where the wakeword was removed
    SILENCE_SECONDS = 0.2

    def __init__(self, audio_data, recognizer, metrics):
        self.audio_data = audio_data
        self.recognizer = recognizer
        self.silence_data = self.__generate_silence(
            self.SILENCE_SECONDS, self.audio_data.sample_rate,
            self.audio_data.sample_width)
        self.wav_data = self.audio_data.get_wav_data()
        self.AUDIO_SIZE = float(len(self.wav_data))
        self.range = self.Range(0, self.AUDIO_SIZE / 2)
        self.metrics = metrics

    class Range:
        def __init__(self, begin, end):
            self.begin = begin
            self.end = end

        def get_marker(self, get_begin):
            if get_begin:
                return self.begin
            else:
                return self.end

        def add_to_marker(self, add_begin, value):
            if add_begin:
                self.begin += value
            else:
                self.end += value

        def narrow(self, value):
            self.begin += value
            self.end -= value

    @staticmethod
    def __found_in_segment(name, byte_data, recognizer, metrics):

        hypothesis = recognizer.transcribe(byte_data, metrics=metrics)
        if hypothesis and hypothesis.hypstr.lower().find(name):
            return True
        else:
            return False

    def audio_pos(self, raw_pos):
        return int(self.audio_data.sample_width *
                   round(float(raw_pos)/self.audio_data.sample_width))

    def get_audio_segment(self, begin, end):
        return self.wav_data[self.audio_pos(begin): self.audio_pos(end)]

    def __calculate_marker(self, use_begin, sign_if_found, range, delta):
        while (2 * delta >= self.MAX_ERROR_SECONDS *
               self.audio_data.sample_rate * self.audio_data.sample_width):
            byte_data = self.get_audio_segment(range.begin, range.end)
            found = self.__found_in_segment(
                "mycroft", byte_data, self.recognizer, self.metrics)
            sign = sign_if_found if found else -sign_if_found
            range.add_to_marker(use_begin, delta * sign)
            delta /= 2
        return range.get_marker(use_begin)

    def calculate_range(self):
        delta = self.AUDIO_SIZE / 4
        self.range.end = self.__calculate_marker(
            False, -1, self.Range(0, self.AUDIO_SIZE / 2), delta)

        # Ensures the end position is well past the wakeword part of the audio
        pos_end_safe = min(
            self.AUDIO_SIZE, self.range.end + self.PUSH_BACK_SECONDS *
            self.audio_data.sample_rate * self.audio_data.sample_width)
        delta = pos_end_safe / 4
        begin = pos_end_safe / 2
        self.range.begin = self.__calculate_marker(
            True, 1, self.Range(begin, pos_end_safe), delta)
        self.range.narrow(self.TRIM_SECONDS * self.audio_data.sample_rate *
                          self.audio_data.sample_width)

    @staticmethod
    def __generate_silence(seconds, sample_rate, sample_width):
        return '\0'*int(seconds * sample_rate * sample_width)

    def get_audio_data_before(self):
        byte_data = self.get_audio_segment(
            0, self.range.begin) + self.silence_data
        return AudioData(
            byte_data, self.audio_data.sample_rate,
            self.audio_data.sample_width)

    def get_audio_data_after(self):
        byte_data = self.silence_data + self.get_audio_segment(
            self.range.end, self.AUDIO_SIZE)
        return AudioData(
            byte_data, self.audio_data.sample_rate,
            self.audio_data.sample_width)


class AudioConsumer(threading.Thread):
    """
    AudioConsumer
    Consumes AudioData chunks off the queue
    """

    # In seconds, the minimum audio size to be sent to remote STT
    MIN_AUDIO_SIZE = 1.0

    def __init__(
            self, state, queue, emitter, wakeup_recognizer,
            wakeword_recognizer, wrapped_remote_recognizer, wakeup_prefixes,
            wakeup_words):
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = queue
        self.state = state
        self.emitter = emitter
        self.wakeup_recognizer = wakeup_recognizer
        self.ww_recognizer = wakeword_recognizer
        self.wrapped_remote_recognizer = wrapped_remote_recognizer
        self.wakeup_prefixes = wakeup_prefixes
        self.wakeup_words = wakeup_words
        self.metrics = MetricsAggregator()

    def run(self):
        while self.state.running:
            self.try_consume_audio()

    @staticmethod
    def _audio_length(audio):
        return float(
            len(audio.frame_data))/(audio.sample_rate*audio.sample_width)

    def try_consume_audio(self):
        timer = Stopwatch()
        hyp = None
        audio = self.queue.get()
        self.metrics.timer(
            "mycroft.recognizer.audio.length_s", self._audio_length(audio))
        self.queue.task_done()
        timer.start()
        if self.state.sleeping:
            hyp = self.wakeup_recognizer.transcribe(
                audio.get_wav_data(), metrics=self.metrics)
            if hyp and hyp.hypstr:
                logger.debug("sleeping recognition: " + hyp.hypstr)
            if hyp and hyp.hypstr.lower().find("wake up") >= 0:
                SessionManager.touch()
                self.state.sleeping = False
                self.__speak("I'm awake.")  # TODO: Localization
                self.metrics.increment("mycroft.wakeup")
        else:
            if not self.state.skip_wakeword:
                hyp = self.ww_recognizer.transcribe(
                    audio.get_wav_data(), metrics=self.metrics)

            if hyp and hyp.hypstr.lower().find("mycroft") >= 0:
                extractor = WakewordExtractor(
                    audio, self.ww_recognizer, self.metrics)
                timer.lap()
                extractor.calculate_range()
                self.metrics.timer(
                    "mycroft.recognizer.extractor.time_s", timer.lap())
                audio_before = extractor.get_audio_data_before()
                self.metrics.timer(
                    "mycroft.recognizer.audio_extracted.length_s",
                    self._audio_length(audio_before))
                audio_after = extractor.get_audio_data_after()
                self.metrics.timer(
                    "mycroft.recognizer.audio_extracted.length_s",
                    self._audio_length(audio_after))

                SessionManager.touch()
                payload = {
                    'utterance': hyp.hypstr,
                    'session': SessionManager.get().session_id,
                    'pos_begin': int(extractor.range.begin),
                    'pos_end': int(extractor.range.end)
                }
                self.emitter.emit("recognizer_loop:wakeword", payload)

                try:
                    self.transcribe([audio_before, audio_after])
                except sr.UnknownValueError:
                    self.__speak("Go ahead")
                    self.state.skip_wakeword = True
                    self.metrics.increment("mycroft.wakeword")

            elif self.state.skip_wakeword:
                SessionManager.touch()
                try:
                    self.transcribe([audio])
                except sr.UnknownValueError:
                    logger.warn(
                        "Speech Recognition could not understand audio")
                    self.__speak("Sorry, I didn't catch that.")
                    self.metrics.increment("mycroft.recognizer.error")
                self.state.skip_wakeword = False
            else:
                self.metrics.clear()
        self.metrics.flush()

    def __speak(self, utterance):
        """
        Speak commands should be asynchronous to avoid filling up the
        portaudio buffer.
        :param utterance:
        :return:
        """
        def target():
            self.emitter.emit(
                "speak",
                Message("speak",
                        metadata={'utterance': utterance,
                                  'session': SessionManager.get().session_id}))

        threading.Thread(target=target).start()

    def _create_remote_stt_runnable(self, audio, utterances):
        def runnable():
            try:
                text = self.wrapped_remote_recognizer.transcribe(
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
        self.microphone = MutableMicrophone(
            sample_rate=sample_rate, device_index=device_index)
        self.microphone.CHANNELS = channels
        self.ww_recognizer = wakeword_recognizer.create_recognizer(
            samprate=sample_rate, lang=lang)
        self.wakeup_recognizer = wakeword_recognizer.create_recognizer(
            samprate=sample_rate, lang=lang,
            keyphrase="wake up mycroft")  # TODO - localization
        self.remote_recognizer = Recognizer()
        basedir = os.path.dirname(__file__)
        self.wakeup_words = read_stripped_lines(os.path.join(
            basedir, 'model', lang, 'WakeUpWord.voc'))
        self.wakeup_prefixes = read_stripped_lines(
            os.path.join(basedir, 'model', lang, 'PrefixWakeUp.voc'))
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
                      self.ww_recognizer,
                      RemoteRecognizerWrapperFactory.wrap_recognizer(
                          self.remote_recognizer),
                      self.wakeup_prefixes,
                      self.wakeup_words).start()

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
                self.stop()
