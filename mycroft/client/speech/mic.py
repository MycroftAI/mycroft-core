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
import audioop
from time import sleep, time as get_time

import collections
import datetime
import json
import os
import pyaudio
import requests
import speech_recognition
from hashlib import md5
from io import BytesIO, StringIO
from speech_recognition import (
    Microphone,
    AudioSource,
    AudioData
)
from threading import Thread, Lock

from mycroft.api import DeviceApi
from mycroft.configuration import Configuration
from mycroft.session import SessionManager
from mycroft.util import (
    check_for_signal,
    get_ipc_directory,
    resolve_resource_file,
    play_wav
)
from mycroft.util.log import LOG


class MutableStream:
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

    def read(self, size, of_exc=False):
        """
            Read data from stream.

            Arguments:
                size (int): Number of bytes to read
                of_exc (bool): flag determining if the audio producer thread
                               should throw IOError at overflows.

            Returns:
                Data read from device
        """
        frames = collections.deque()
        remaining = size
        while remaining > 0:
            to_read = min(self.wrapped_stream.get_read_available(), remaining)
            if to_read == 0:
                sleep(.01)
                continue
            result = self.wrapped_stream.read(to_read,
                                              exception_on_overflow=of_exc)
            frames.append(result)
            remaining -= to_read

        if self.muted:
            return self.muted_buffer
        input_latency = self.wrapped_stream.get_input_latency()
        if input_latency > 0.2:
            LOG.warning("High input latency: %f" % input_latency)
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
    def __init__(self, device_index=None, sample_rate=16000, chunk_size=1024,
                 mute=False):
        Microphone.__init__(
            self, device_index=device_index, sample_rate=sample_rate,
            chunk_size=chunk_size)
        self.muted = False
        if mute:
            self.mute()

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

    def is_muted(self):
        return self.muted


def get_silence(num_bytes):
    return b'\0' * num_bytes


class ResponsiveRecognizer(speech_recognition.Recognizer):
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

        self.config = Configuration.get()
        listener_config = self.config.get('listener')
        self.upload_url = listener_config['wake_word_upload']['url']
        self.upload_disabled = listener_config['wake_word_upload']['disable']
        self.wake_word_name = wake_word_recognizer.key_phrase

        self.overflow_exc = listener_config.get('overflow_exception', False)

        speech_recognition.Recognizer.__init__(self)
        self.wake_word_recognizer = wake_word_recognizer
        self.audio = pyaudio.PyAudio()
        self.multiplier = listener_config.get('multiplier')
        self.energy_ratio = listener_config.get('energy_ratio')
        # check the config for the flag to save wake words.

        if 'record_utterances' in listener_config:
            # TODO: 19.08 remove this backwards compatibility
            self.save_utterances = listener_config.get('record_utterances')
        else:
            self.save_utterances = listener_config.get('save_utterances',
                                                       False)
        self.upload_lock = Lock()
        self.filenames_to_upload = []
        self.mic_level_file = os.path.join(get_ipc_directory(), "mic_level")
        self._stop_signaled = False

        # The maximum audio in seconds to keep for transcribing a phrase
        # The wake word must fit in this time
        num_phonemes = wake_word_recognizer.num_phonemes
        len_phoneme = listener_config.get('phoneme_duration', 120) / 1000.0
        self.TEST_WW_SEC = num_phonemes * len_phoneme
        self.SAVED_WW_SEC = max(3, self.TEST_WW_SEC)

        try:
            self.account_id = DeviceApi().get()['user']['uuid']
        except (requests.RequestException, AttributeError):
            self.account_id = '0'

    def record_sound_chunk(self, source):
        return source.stream.read(source.CHUNK, self.overflow_exc)

    @staticmethod
    def calc_energy(sound_chunk, sample_width):
        return audioop.rms(sound_chunk, sample_width)

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
        byte_data = get_silence(source.SAMPLE_WIDTH)

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

            # Pressing top-button will end recording immediately
            if check_for_signal('buttonPress'):
                phrase_complete = True

        return byte_data

    @staticmethod
    def sec_to_bytes(sec, source):
        return int(sec * source.SAMPLE_RATE) * source.SAMPLE_WIDTH

    def _skip_wake_word(self):
        # Check if told programatically to skip the wake word, like
        # when we are in a dialog with the user.
        if check_for_signal('startListening'):
            return True

        # Pressing the Mark 1 button can start recording (unless
        # it is being used to mean 'stop' instead)
        if check_for_signal('buttonPress', 1):
            # give other processes time to consume this signal if
            # it was meant to be a 'stop'
            sleep(0.25)
            if check_for_signal('buttonPress'):
                # Signal is still here, assume it was intended to
                # begin recording
                LOG.debug("Button Pressed, wakeword not needed")
                return True

        return False

    def stop(self):
        """
            Signal stop and exit waiting state.
        """
        self._stop_signaled = True

    def _upload_wake_word(self, audio):
        ww_module = self.wake_word_recognizer.__class__.__name__
        if ww_module == 'PreciseHotword':
            model_path = self.wake_word_recognizer.precise_model
            with open(model_path, 'rb') as f:
                model_hash = md5(f.read()).hexdigest()
        else:
            model_hash = '0'

        metadata = {
            'name': self.wake_word_name.replace(' ', '-'),
            'engine': md5(ww_module.encode('utf-8')).hexdigest(),
            'time': str(int(1000 * get_time())),
            'sessionId': SessionManager.get().session_id,
            'accountId': self.account_id,
            'model': str(model_hash)
        }
        requests.post(
            self.upload_url, files={
                'audio': BytesIO(audio.get_wav_data()),
                'metadata': StringIO(json.dumps(metadata))
            }
        )

    def _wait_until_wake_word(self, source, sec_per_buffer):
        """Listen continuously on source until a wake word is spoken

        Args:
            source (AudioSource):  Source producing the audio chunks
            sec_per_buffer (float):  Fractional number of seconds in each chunk
        """
        num_silent_bytes = int(self.SILENCE_SEC * source.SAMPLE_RATE *
                               source.SAMPLE_WIDTH)

        silence = get_silence(num_silent_bytes)

        # bytearray to store audio in
        byte_data = silence

        buffers_per_check = self.SEC_BETWEEN_WW_CHECKS / sec_per_buffer
        buffers_since_check = 0.0

        # Max bytes for byte_data before audio is removed from the front
        max_size = self.sec_to_bytes(self.SAVED_WW_SEC, source)
        test_size = self.sec_to_bytes(self.TEST_WW_SEC, source)

        said_wake_word = False

        # Rolling buffer to track the audio energy (loudness) heard on
        # the source recently.  An average audio energy is maintained
        # based on these levels.
        energies = []
        idx_energy = 0
        avg_energy = 0.0
        energy_avg_samples = int(5 / sec_per_buffer)  # avg over last 5 secs
        counter = 0

        while not said_wake_word and not self._stop_signaled:
            if self._skip_wake_word():
                break
            chunk = self.record_sound_chunk(source)

            energy = self.calc_energy(chunk, source.SAMPLE_WIDTH)
            if energy < self.energy_threshold * self.multiplier:
                self._adjust_threshold(energy, sec_per_buffer)

            if len(energies) < energy_avg_samples:
                # build the average
                energies.append(energy)
                avg_energy += float(energy) / energy_avg_samples
            else:
                # maintain the running average and rolling buffer
                avg_energy -= float(energies[idx_energy]) / energy_avg_samples
                avg_energy += float(energy) / energy_avg_samples
                energies[idx_energy] = energy
                idx_energy = (idx_energy + 1) % energy_avg_samples

                # maintain the threshold using average
                if energy < avg_energy * 1.5:
                    if energy > self.energy_threshold:
                        # bump the threshold to just above this value
                        self.energy_threshold = energy * 1.2

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
            self.wake_word_recognizer.update(chunk)
            if buffers_since_check > buffers_per_check:
                buffers_since_check -= buffers_per_check
                chopped = byte_data[-test_size:] \
                    if test_size < len(byte_data) else byte_data
                audio_data = chopped + silence
                said_wake_word = \
                    self.wake_word_recognizer.found_wake_word(audio_data)
                # if a wake word is success full then upload wake word
                if said_wake_word and self.config['opt_in'] and not \
                        self.upload_disabled:
                    Thread(
                        target=self._upload_wake_word, daemon=True,
                        args=[self._create_audio_data(byte_data, source)]
                    ).start()

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

        LOG.debug("Waiting for wake word...")
        self._wait_until_wake_word(source, sec_per_buffer)
        if self._stop_signaled:
            return

        LOG.debug("Recording...")
        emitter.emit("recognizer_loop:record_begin")

        # If enabled, play a wave file with a short sound to audibly
        # indicate recording has begun.
        if self.config.get('confirm_listening'):
            file = resolve_resource_file(
                self.config.get('sounds').get('start_listening'))
            if file:
                play_wav(file)

        frame_data = self._record_phrase(source, sec_per_buffer)
        audio_data = self._create_audio_data(frame_data, source)
        emitter.emit("recognizer_loop:record_end")
        if self.save_utterances:
            LOG.info("Recording utterance")
            stamp = str(datetime.datetime.now())
            filename = "/tmp/mycroft_utterance%s.wav" % stamp
            with open(filename, 'wb') as filea:
                filea.write(audio_data.get_wav_data())
            LOG.debug("Thinking...")

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
