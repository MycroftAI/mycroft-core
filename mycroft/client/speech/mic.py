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


import collections
import audioop
from time import sleep

import pyaudio
from speech_recognition import (
    Microphone,
    AudioSource,
    WaitTimeoutError,
    AudioData
)
import speech_recognition
from mycroft.util.log import getLogger

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
        self.muted = True

    def unmute(self):
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
    MIN_LOUD_SEC_PER_PHRASE = 0.2

    # The maximum length a phrase can be recorded,
    # provided there is noise the entire time
    RECORDING_TIMEOUT = 30.0

    # Time between pocketsphinx checks for the wake word
    SEC_BETWEEN_WW_CHECKS = 0.2

    def __init__(self, wake_word_recognizer):
        speech_recognition.Recognizer.__init__(self)
        self.daemon = True

        self.wake_word_recognizer = wake_word_recognizer
        self.audio = pyaudio.PyAudio()

    @staticmethod
    def record_sound_chunk(source):
        return source.stream.read(source.CHUNK)

    @staticmethod
    def calc_energy(sound_chunk, sample_width):
        return audioop.rms(sound_chunk, sample_width)

    def wake_word_in_audio(self, frame_data):
        hyp = self.wake_word_recognizer.transcribe(frame_data)
        return self.wake_word_recognizer.found_wake_word(hyp)

    def record_phrase(self, source, sec_per_buffer):
        """
        This attempts to record an entire spoken phrase. Essentially,
        this waits for a period of silence and then returns the audio

        :rtype: bytearray
        :param source: AudioSource
        :param sec_per_buffer: Based on source.SAMPLE_RATE
        :return: bytearray representing the frame_data of the recorded phrase
        """
        num_loud_chunks = 0
        noise = 0

        max_noise = 20
        min_noise = 0

        def increase_noise(level):
            if level < max_noise:
                return level + 2
            return level

        def decrease_noise(level):
            if level > min_noise:
                return level - 1
            return level

        # Smallest number of loud chunks required to return
        min_loud_chunks = int(self.MIN_LOUD_SEC_PER_PHRASE / sec_per_buffer)

        # bytearray to store audio in
        byte_data = '\0' * source.SAMPLE_WIDTH

        phrase_complete = False
        while not phrase_complete:
            chunk = self.record_sound_chunk(source)
            byte_data = byte_data + chunk

            energy = self.calc_energy(chunk, source.SAMPLE_WIDTH)
            is_loud = energy > self.energy_threshold
            if is_loud:
                noise = increase_noise(noise)
                num_loud_chunks += 1
            else:
                noise = decrease_noise(noise)
                self.adjust_threshold(energy, sec_per_buffer)

            if noise <= min_noise and num_loud_chunks > min_loud_chunks:
                phrase_complete = True

        return byte_data

    @staticmethod
    def sec_to_bytes(sec, source):
        return sec * source.SAMPLE_RATE * source.SAMPLE_WIDTH

    def wait_until_wake_word(self, source, sec_per_buffer):
        num_silent_bytes = int(self.SILENCE_SEC * source.SAMPLE_RATE *
                               source.SAMPLE_WIDTH)

        silence = '\0' * num_silent_bytes

        # bytearray to store audio in
        byte_data = silence

        buffers_per_check = self.SEC_BETWEEN_WW_CHECKS / sec_per_buffer
        buffers_since_check = 0.0

        # Max bytes for byte_data before audio is removed from the front
        max_size = self.sec_to_bytes(self.SAVED_WW_SEC, source)

        said_wake_word = False
        while not said_wake_word:
            chunk = self.record_sound_chunk(source)

            energy = self.calc_energy(chunk, source.SAMPLE_WIDTH)
            if energy < self.energy_threshold:
                self.adjust_threshold(energy, sec_per_buffer)

            needs_to_grow = len(byte_data) < max_size
            if needs_to_grow:
                byte_data = byte_data + chunk
            else:  # Remove beginning of audio and add new chunk to end
                byte_data = byte_data[len(chunk):] + chunk

            buffers_since_check += 1.0
            if buffers_since_check < buffers_per_check:
                buffers_since_check -= buffers_per_check
                said_wake_word = self.wake_word_in_audio(byte_data + silence)

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
        sec_per_buffer = float(source.CHUNK) / bytes_per_sec

        logger.debug("Waiting for wake word...")
        self.wait_until_wake_word(source, sec_per_buffer)

        logger.debug("Recording...")
        emitter.emit("recognizer_loop:record_begin")
        frame_data = self.record_phrase(source, sec_per_buffer)
        audio_data = self.create_audio_data(frame_data, source)
        emitter.emit("recognizer_loop:record_end")
        logger.debug("Thinking...")

        return audio_data

    def adjust_threshold(self, energy, seconds_per_buffer):
        if self.dynamic_energy_threshold and energy > 0:
            # account for different chunk sizes and rates
            damping = (
                self.dynamic_energy_adjustment_damping ** seconds_per_buffer)
            target_energy = energy * self.dynamic_energy_ratio
            self.energy_threshold = (
                self.energy_threshold * damping +
                target_energy * (1 - damping))
