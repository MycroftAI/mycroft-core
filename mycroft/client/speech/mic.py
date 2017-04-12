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


import audioop
import collections
from time import sleep

import pyaudio
import speech_recognition
from speech_recognition import (
    Microphone,
    AudioSource,
    AudioData
)

from mycroft.client.speech.local_recognizer import LocalRecognizer
from mycroft.configuration import ConfigurationManager
from mycroft.util import check_for_signal
from mycroft.util.log import getLogger

listener_config = ConfigurationManager.get().get('listener')
logger = getLogger(__name__)
__author__ = 'seanfitz'


class MutableStream(object):
    def __init__(self, wrapped_stream, format, muted=False):
        assert wrapped_stream is not None
        self.wrapped_stream = wrapped_stream
        self.muted = muted
        self.SAMPLE_WIDTH = pyaudio.get_sample_size(format)
        self.muted_buffer = b''.join([b'\x00' * self.SAMPLE_WIDTH])

    def mute(self):
        logger.debug("muted")
        self.muted = True

    def unmute(self):
        logger.debug("unmuted")
        self.muted = False

    def read(self, size):
        frames = collections.deque()
        remaining = size
        while remaining > 0:
            to_read = min(self.wrapped_stream.get_read_available(), remaining)
            if to_read == 0:
                sleep(.01)
                continue
            result = self.wrapped_stream.read(to_read)
            frames.append(result)
            remaining -= to_read

        if self.muted:
            return self.muted_buffer
        input_latency = self.wrapped_stream.get_input_latency()
        if input_latency > 0.2:
            logger.warn("High input latency: %f" % input_latency)
        audio = b"".join(list(frames))
        return audio

    def close(self):
        self.wrapped_stream.close()
        self.wrapped_stream = None

    def is_stopped(self):
        return self.wrapped_stream.is_stopped()

    def stop_stream(self):
        return self.wrapped_stream.stop_stream()


class MutableMicrophone(Microphone):
    def __init__(self, device_index=None, sample_rate=16000, chunk_size=1024):
        Microphone.__init__(
            self, device_index=device_index, sample_rate=sample_rate,
            chunk_size=chunk_size)
        self.muted = False

    def __enter__(self):
        assert self.stream is None, \
            "This audio source is already inside a context manager"
        self.audio = pyaudio.PyAudio()
        self.stream = MutableStream(self.audio.open(
            input_device_index=self.device_index, channels=1,
            format=self.format, rate=self.SAMPLE_RATE,
            frames_per_buffer=self.CHUNK,
            input=True,  # stream is an input stream
        ), self.format, self.muted)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.stream.is_stopped():
            self.stream.stop_stream()
        self.stream.close()
        self.stream = None
        self.audio.terminate()

    def mute(self):
        self.muted = True
        if self.stream:
            self.stream.mute()

    def unmute(self):
        self.muted = False
        if self.stream:
            self.stream.unmute()


class ResponsiveRecognizer(speech_recognition.Recognizer):
    # The maximum audio in seconds to keep for transcribing a phrase
    # The wake word must fit in this time
    SAVED_WW_SEC = 1.0

    # Padding of silence when feeding to pocketsphinx
    SILENCE_SEC = 0.01

    # The minimum seconds of noise before a
    # phrase can be considered complete
    MIN_LOUD_SEC_PER_PHRASE = 0.1

    # The maximum length a phrase can be recorded,
    # provided there is noise the entire time
    RECORDING_TIMEOUT = 10.0

    # The maximum time it will continue to record silence
    # when not enough noise has been detected
    RECORDING_TIMEOUT_WITH_SILENCE = 3.0

    # Time between pocketsphinx checks for the wake word
    SEC_BETWEEN_WW_CHECKS = 0.2

    def __init__(self, wake_word_recognizer):
        speech_recognition.Recognizer.__init__(self)
        self.wake_word_recognizer = wake_word_recognizer
#        self.audio = pyaudio.PyAudio()
        self.multiplier = listener_config.get('multiplier')
        self.energy_ratio = listener_config.get('energy_ratio')
        self.forced_wake = False

    @staticmethod
    def record_sound_chunk(source):
        return source.stream.read(source.CHUNK)

    @staticmethod
    def calc_energy(sound_chunk, sample_width):
        res = audioop.rms(sound_chunk, sample_width)
#	logger.debug("energy=%s",res)
        return res

    def record_phrase(self, source, sec_per_buffer):
        in_speech=False
        LocalRecognizer.decoder.set_search('command')
        LocalRecognizer.decoder.start_utt()
        logger.debug("Waiting for command...")
        while True:
            chunk = self.record_sound_chunk(source)

            LocalRecognizer.decoder.process_raw(chunk, False, False)
            new_in_speech = LocalRecognizer.decoder.get_in_speech()
            logger.debug("in_speech=%s new_in_speech=%s",in_speech,new_in_speech)
            if new_in_speech:
                # voice
                in_speech=True
            else:
                # silence
                if in_speech:
                    in_speech=False
                    LocalRecognizer.decoder.end_utt()
                    hyp = LocalRecognizer.decoder.hyp()
                    if hyp:
                        logger.debug("utt=%s",hyp.hypstr)
                        return (None,hyp.hypstr)
                    LocalRecognizer.decoder.start_utt()

    @staticmethod
    def sec_to_bytes(sec, source):
        return sec * source.SAMPLE_RATE * source.SAMPLE_WIDTH

    def wait_until_wake_word(self, source, sec_per_buffer):
        # bytearray to store audio in
        byte_data = ""

        buffers_per_check = self.SEC_BETWEEN_WW_CHECKS / sec_per_buffer
        buffers_since_check = 0.0

        # Max bytes for byte_data before audio is removed from the front
        max_size = self.sec_to_bytes(self.SAVED_WW_SEC, source)

        in_speech=False
        LocalRecognizer.decoder.set_search('wake_up')
        LocalRecognizer.decoder.start_utt()
        logger.debug("Waiting for wake word...")
        while True:
            if self.forced_wake or check_for_signal('buttonPress'):
                self.forced_wake = False
                said_wake_word = True
                continue

            chunk = self.record_sound_chunk(source)

            if len(byte_data) < max_size:
                byte_data += chunk
            else:  # Remove beginning of audio and add new chunk to end
                byte_data = byte_data[len(chunk):] + chunk

            buffers_since_check += 1.0
            if buffers_since_check > buffers_per_check:
                buffers_since_check -= buffers_per_check
                LocalRecognizer.decoder.process_raw(byte_data, False, False)
                if LocalRecognizer.decoder.get_in_speech():
                    in_speech=True
                else:
                    if in_speech:
                        in_speech=False
                        LocalRecognizer.decoder.end_utt()
                        hyp = LocalRecognizer.decoder.hyp()
                        if self.wake_word_recognizer.found_wake_word(hyp):
                            break
                        LocalRecognizer.decoder.start_utt()
       

    @staticmethod
    def create_audio_data(raw_data, source):
        """
        Constructs an AudioData instance with the same parameters
        as the source and the specified frame_data
        """
        return AudioData(raw_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)

    def listen(self, source, emitter):
        """
        Listens for audio that Mycroft should respond to

        :param source: an ``AudioSource`` instance for reading from
        :param emitter: a pyee EventEmitter for sending when the wakeword
                        has been found
        """
        assert isinstance(source, AudioSource), "Source must be an AudioSource"

        bytes_per_sec = source.SAMPLE_RATE * source.SAMPLE_WIDTH
        sec_per_buffer = float(source.CHUNK) / source.SAMPLE_RATE

        self.wait_until_wake_word(source, sec_per_buffer)
        logger.debug("wake_word detected")

        emitter.emit("recognizer_loop:record_begin")
        logger.debug("recording...")
        record = self.record_phrase(source, sec_per_buffer)
        logger.debug("recorded.")
        emitter.emit("recognizer_loop:record_end")

        if record[0]:
            audio_data = self.create_audio_data(record[0], source)
        else:
            audio_data = None

        return (audio_data,record[1])

    def force_wake(self):
        self.forced_wake = True


