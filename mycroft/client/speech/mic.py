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
import os
from time import sleep

import pyaudio
import speech_recognition
from speech_recognition import (
    Microphone,
    AudioSource,
    AudioData
)

from mycroft.configuration import ConfigurationManager
from mycroft.util import (
    check_for_signal,
    get_ipc_directory,
    resolve_resource_file,
    play_wav
)
from mycroft.util.log import getLogger

config = ConfigurationManager.get()
listener_config = config.get('listener')
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
    MIN_LOUD_SEC_PER_PHRASE = 0.5

    # The minimum seconds of silence required at the end
    # before a phrase will be considered complete
    MIN_SILENCE_AT_END = 0.25

    # The maximum seconds a phrase can be recorded,
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
        self.audio = pyaudio.PyAudio()
        self.multiplier = listener_config.get('multiplier')
        self.energy_ratio = listener_config.get('energy_ratio')
        self.mic_level_file = os.path.join(get_ipc_directory(), "mic_level")

    @staticmethod
    def record_sound_chunk(source):
        return source.stream.read(source.CHUNK)

    @staticmethod
    def calc_energy(sound_chunk, sample_width):
        return audioop.rms(sound_chunk, sample_width)

    def wake_word_in_audio(self, frame_data):
        hyp = self.wake_word_recognizer.transcribe(frame_data)
        return self.wake_word_recognizer.found_wake_word(hyp)

    def _record_phrase(self, source, sec_per_buffer):
        """Record an entire spoken phrase.

        Essentially, this code waits for a period of silence and then returns
        the audio.  If silence isn't detected, it will terminate and return
        a buffer of RECORDING_TIMEOUT duration.

        Args:
            source (AudioSource):  Source producing the audio chunks
            sec_per_buffer (float):  Fractional number of seconds in each chunk

        Returns:
            bytearray: complete audio buffer recorded, including any
                       silence at the end of the user's utterance
        """

        num_loud_chunks = 0
        noise = 0

        max_noise = 25
        min_noise = 0

        silence_duration = 0

        def increase_noise(level):
            if level < max_noise:
                return level + 200 * sec_per_buffer
            return level

        def decrease_noise(level):
            if level > min_noise:
                return level - 100 * sec_per_buffer
            return level

        # Smallest number of loud chunks required to return
        min_loud_chunks = int(self.MIN_LOUD_SEC_PER_PHRASE / sec_per_buffer)

        # Maximum number of chunks to record before timing out
        max_chunks = int(self.RECORDING_TIMEOUT / sec_per_buffer)
        num_chunks = 0

        # Will return if exceeded this even if there's not enough loud chunks
        max_chunks_of_silence = int(self.RECORDING_TIMEOUT_WITH_SILENCE /
                                    sec_per_buffer)

        # bytearray to store audio in
        byte_data = '\0' * source.SAMPLE_WIDTH

        phrase_complete = False
        while num_chunks < max_chunks and not phrase_complete:
            chunk = self.record_sound_chunk(source)
            byte_data += chunk
            num_chunks += 1

            energy = self.calc_energy(chunk, source.SAMPLE_WIDTH)
            test_threshold = self.energy_threshold * self.multiplier
            is_loud = energy > test_threshold
            if is_loud:
                noise = increase_noise(noise)
                num_loud_chunks += 1
            else:
                noise = decrease_noise(noise)
                self._adjust_threshold(energy, sec_per_buffer)

            if num_chunks % 10 == 0:
                with open(self.mic_level_file, 'w') as f:
                    f.write("Energy:  cur=" + str(energy) + " thresh=" +
                            str(self.energy_threshold))
                f.close()

            was_loud_enough = num_loud_chunks > min_loud_chunks

            quiet_enough = noise <= min_noise
            if quiet_enough:
                silence_duration += sec_per_buffer
                if silence_duration < self.MIN_SILENCE_AT_END:
                    quiet_enough = False  # gotta be silent for min of 1/4 sec
            else:
                silence_duration = 0
            recorded_too_much_silence = num_chunks > max_chunks_of_silence
            if quiet_enough and (was_loud_enough or recorded_too_much_silence):
                phrase_complete = True
            if check_for_signal('buttonPress'):
                phrase_complete = True

        return byte_data

    @staticmethod
    def sec_to_bytes(sec, source):
        return sec * source.SAMPLE_RATE * source.SAMPLE_WIDTH

    def _wait_until_wake_word(self, source, sec_per_buffer):
        """Listen continuously on source until a wake word is spoken

        Args:
            source (AudioSource):  Source producing the audio chunks
            sec_per_buffer (float):  Fractional number of seconds in each chunk
        """
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

        # Rolling buffer to track the audio energy (loudness) heard on
        # the source recently.  An average audio energy is maintained
        # based on these levels.
        energies = []
        idx_energy = 0
        avg_energy = 0.0
        energy_avg_samples = int(5 / sec_per_buffer)  # avg over last 5 secs

        counter = 0

        while not said_wake_word:
            if check_for_signal('buttonPress'):
                said_wake_word = True
                continue

            chunk = self.record_sound_chunk(source)

            energy = self.calc_energy(chunk, source.SAMPLE_WIDTH)
            if energy < self.energy_threshold * self.multiplier:
                self._adjust_threshold(energy, sec_per_buffer)

            if len(energies) < energy_avg_samples:
                # build the average
                energies.append(energy)
                avg_energy += float(energy)/energy_avg_samples
            else:
                # maintain the running average and rolling buffer
                avg_energy -= float(energies[idx_energy])/energy_avg_samples
                avg_energy += float(energy)/energy_avg_samples
                energies[idx_energy] = energy
                idx_energy = (idx_energy+1) % energy_avg_samples

                # maintain the threshold using average
                if energy < avg_energy*1.5:
                    if energy > self.energy_threshold:
                        # bump the threshold to just above this value
                        self.energy_threshold = energy*1.2

            # Periodically output energy level stats.  This can be used to
            # visualize the microphone input, e.g. a needle on a meter.
            if counter % 3:
                with open(self.mic_level_file, 'w') as f:
                    f.write("Energy:  cur=" + str(energy) + " thresh=" +
                            str(self.energy_threshold))
                f.close()
            counter += 1

            # At first, the buffer is empty and must fill up.  After that
            # just drop the first chunk bytes to keep it the same size.
            needs_to_grow = len(byte_data) < max_size
            if needs_to_grow:
                byte_data += chunk
            else:  # Remove beginning of audio and add new chunk to end
                byte_data = byte_data[len(chunk):] + chunk

            buffers_since_check += 1.0
            if buffers_since_check > buffers_per_check:
                buffers_since_check -= buffers_per_check
                said_wake_word = self.wake_word_in_audio(byte_data + silence)

    @staticmethod
    def _create_audio_data(raw_data, source):
        """
        Constructs an AudioData instance with the same parameters
        as the source and the specified frame_data
        """
        return AudioData(raw_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)

    def listen(self, source, emitter):
        """Listens for chunks of audio that Mycroft should perform STT on.

        This will listen continuously for a wake-up-word, then return the
        audio chunk containing the spoken phrase that comes immediately
        afterwards.

        Args:
            source (AudioSource):  Source producing the audio chunks
            emitter (EventEmitter): Emitter for notifications of when recording
                                    begins and ends.

        Returns:
            AudioData: audio with the user's utterance, minus the wake-up-word
        """
        assert isinstance(source, AudioSource), "Source must be an AudioSource"

#        bytes_per_sec = source.SAMPLE_RATE * source.SAMPLE_WIDTH
        sec_per_buffer = float(source.CHUNK) / source.SAMPLE_RATE

        # Every time a new 'listen()' request begins, reset the threshold
        # used for silence detection.  This is as good of a reset point as
        # any, as we expect the user and Mycroft to not be talking.
        # NOTE: adjust_for_ambient_noise() doc claims it will stop early if
        #       speech is detected, but there is no code to actually do that.
        self.adjust_for_ambient_noise(source, 1.0)

        logger.debug("Waiting for wake word...")
        self._wait_until_wake_word(source, sec_per_buffer)

        logger.debug("Recording...")
        emitter.emit("recognizer_loop:record_begin")

        # If enabled, play a wave file with a short sound to audibly
        # indicate recording has begun.
        if config.get('confirm_listening'):
            file = resolve_resource_file(
                config.get('sounds').get('start_listening'))
            if file:
                play_wav(file)

        frame_data = self._record_phrase(source, sec_per_buffer)
        audio_data = self._create_audio_data(frame_data, source)
        emitter.emit("recognizer_loop:record_end")
        logger.debug("Thinking...")

        return audio_data

    def _adjust_threshold(self, energy, seconds_per_buffer):
        if self.dynamic_energy_threshold and energy > 0:
            # account for different chunk sizes and rates
            damping = (
                self.dynamic_energy_adjustment_damping ** seconds_per_buffer)
            target_energy = energy * self.energy_ratio
            self.energy_threshold = (
                self.energy_threshold * damping +
                target_energy * (1 - damping))
