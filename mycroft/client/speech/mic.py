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

from collections import deque
import datetime
import json
import os
from os.path import isdir, join
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
from tempfile import gettempdir
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

        self.SAMPLE_WIDTH = pyaudio.get_sample_size(format)
        self.muted_buffer = b''.join([b'\x00' * self.SAMPLE_WIDTH])
        self.read_lock = Lock()

        self.muted = muted
        if muted:
            self.mute()

    def mute(self):
        """Stop the stream and set the muted flag."""
        with self.read_lock:
            self.muted = True
            self.wrapped_stream.stop_stream()

    def unmute(self):
        """Start the stream and clear the muted flag."""
        with self.read_lock:
            self.muted = False
            self.wrapped_stream.start_stream()

    def read(self, size, of_exc=False):
        """Read data from stream.

        Arguments:
            size (int): Number of bytes to read
            of_exc (bool): flag determining if the audio producer thread
                           should throw IOError at overflows.

        Returns:
            (bytes) Data read from device
        """
        frames = deque()
        remaining = size
        with self.read_lock:
            while remaining > 0:
                # If muted during read return empty buffer. This ensures no
                # reads occur while the stream is stopped
                if self.muted:
                    return self.muted_buffer

                to_read = min(self.wrapped_stream.get_read_available(),
                              remaining)
                if to_read <= 0:
                    sleep(.01)
                    continue
                result = self.wrapped_stream.read(to_read,
                                                  exception_on_overflow=of_exc)
                frames.append(result)
                remaining -= to_read

        input_latency = self.wrapped_stream.get_input_latency()
        if input_latency > 0.2:
            LOG.warning("High input latency: %f" % input_latency)
        audio = b"".join(list(frames))
        return audio

    def close(self):
        self.wrapped_stream.close()
        self.wrapped_stream = None

    def is_stopped(self):
        try:
            return self.wrapped_stream.is_stopped()
        except Exception as e:
            LOG.error(repr(e))
            return True  # Assume the stream has been closed and thusly stopped

    def stop_stream(self):
        return self.wrapped_stream.stop_stream()


class MutableMicrophone(Microphone):
    def __init__(self, device_index=None, sample_rate=16000, chunk_size=1024,
                 mute=False):
        Microphone.__init__(self, device_index=device_index,
                            sample_rate=sample_rate, chunk_size=chunk_size)
        self.muted = False
        if mute:
            self.mute()

    def __enter__(self):
        return self._start()

    def _start(self):
        """Open the selected device and setup the stream."""
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
        return self._stop()

    def _stop(self):
        """Stop and close an open stream."""
        try:
            if not self.stream.is_stopped():
                self.stream.stop_stream()
            self.stream.close()
        except Exception:
            LOG.exception('Failed to stop mic input stream')
            # Let's pretend nothing is wrong...

        self.stream = None
        self.audio.terminate()

    def restart(self):
        """Shutdown input device and restart."""
        self._stop()
        self._start()

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

    # TODO: Remove in 20.08
    # The maximum seconds a phrase can be recorded,
    # provided there is noise the entire time
    RECORDING_TIMEOUT = 10.0

    # TODO: Remove in 20.08
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

        # Check the config for the flag to save wake words, utterances
        # and for a path under which to save them
        self.save_utterances = listener_config.get('save_utterances', False)
        self.save_wake_words = listener_config.get('record_wake_words', False)
        self.save_path = listener_config.get('save_path', gettempdir())
        self.saved_wake_words_dir = join(self.save_path, 'mycroft_wake_words')
        if self.save_wake_words and not isdir(self.saved_wake_words_dir):
            os.mkdir(self.saved_wake_words_dir)
        self.saved_utterances_dir = join(self.save_path, 'mycroft_utterances')
        if self.save_utterances and not isdir(self.saved_utterances_dir):
            os.mkdir(self.saved_utterances_dir)

        self.upload_lock = Lock()
        self.filenames_to_upload = []
        self.mic_level_file = os.path.join(get_ipc_directory(), "mic_level")

        # Signal statuses
        self._stop_signaled = False
        self._listen_triggered = False

        # The maximum audio in seconds to keep for transcribing a phrase
        # The wake word must fit in this time
        num_phonemes = wake_word_recognizer.num_phonemes
        len_phoneme = listener_config.get('phoneme_duration', 120) / 1000.0
        self.TEST_WW_SEC = num_phonemes * len_phoneme
        self.SAVED_WW_SEC = max(3, self.TEST_WW_SEC)

        self._account_id = None

        # The maximum seconds a phrase can be recorded,
        # provided there is noise the entire time
        self.recording_timeout = listener_config.get('recording_timeout',
                                                     self.RECORDING_TIMEOUT)

        # The maximum time it will continue to record silence
        # when not enough noise has been detected
        self.recording_timeout_with_silence = listener_config.get(
            'recording_timeout_with_silence',
            self.RECORDING_TIMEOUT_WITH_SILENCE)

    @property
    def account_id(self):
        """Fetch account from backend when needed.

        If an error occurs it's handled and a temporary value is returned.
        When a value is received it will be cached until next start.
        """
        if not self._account_id:
            try:
                self._account_id = DeviceApi().get()['user']['uuid']
            except (requests.RequestException, AttributeError):
                pass  # These are expected and won't be reported
            except Exception as e:
                LOG.debug('Unhandled exception while determining device_id, '
                          'Error: {}'.format(repr(e)))

        return self._account_id or '0'

    def record_sound_chunk(self, source):
        return source.stream.read(source.CHUNK, self.overflow_exc)

    @staticmethod
    def calc_energy(sound_chunk, sample_width):
        return audioop.rms(sound_chunk, sample_width)

    def _record_phrase(
        self,
        source,
        sec_per_buffer,
        stream=None,
        ww_frames=None
    ):
        """Record an entire spoken phrase.

        Essentially, this code waits for a period of silence and then returns
        the audio.  If silence isn't detected, it will terminate and return
        a buffer of self.recording_timeout duration.

        Args:
            source (AudioSource):  Source producing the audio chunks
            sec_per_buffer (float):  Fractional number of seconds in each chunk
            stream (AudioStreamHandler): Stream target that will receive chunks
                                         of the utterance audio while it is
                                         being recorded.
            ww_frames (deque):  Frames of audio data from the last part of wake
                                word detection.

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
        max_chunks = int(self.recording_timeout / sec_per_buffer)
        num_chunks = 0

        # Will return if exceeded this even if there's not enough loud chunks
        max_chunks_of_silence = int(self.recording_timeout_with_silence /
                                    sec_per_buffer)

        # bytearray to store audio in
        byte_data = get_silence(source.SAMPLE_WIDTH)

        if stream:
            stream.stream_start()

        phrase_complete = False
        while num_chunks < max_chunks and not phrase_complete:
            if ww_frames:
                chunk = ww_frames.popleft()
            else:
                chunk = self.record_sound_chunk(source)
            byte_data += chunk
            num_chunks += 1

            if stream:
                stream.stream_chunk(chunk)

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
                self.write_mic_level(energy, source)

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

    def write_mic_level(self, energy, source):
        with open(self.mic_level_file, 'w') as f:
            f.write('Energy:  cur={} thresh={:.3f} muted={}'.format(
                energy,
                self.energy_threshold,
                int(source.muted)
                )
            )

    @staticmethod
    def sec_to_bytes(sec, source):
        return int(sec * source.SAMPLE_RATE) * source.SAMPLE_WIDTH

    def _skip_wake_word(self):
        """Check if told programatically to skip the wake word

        For example when we are in a dialog with the user.
        """
        # TODO: remove startListening signal check in 20.02
        if check_for_signal('startListening') or self._listen_triggered:
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

    def _compile_metadata(self):
        ww_module = self.wake_word_recognizer.__class__.__name__
        if ww_module == 'PreciseHotword':
            model_path = self.wake_word_recognizer.precise_model
            with open(model_path, 'rb') as f:
                model_hash = md5(f.read()).hexdigest()
        else:
            model_hash = '0'

        return {
            'name': self.wake_word_name.replace(' ', '-'),
            'engine': md5(ww_module.encode('utf-8')).hexdigest(),
            'time': str(int(1000 * get_time())),
            'sessionId': SessionManager.get().session_id,
            'accountId': self.account_id,
            'model': str(model_hash)
        }

    def _upload_wake_word(self, audio, metadata):
        requests.post(
            self.upload_url, files={
                'audio': BytesIO(audio.get_wav_data()),
                'metadata': StringIO(json.dumps(metadata))
            }
        )

    def trigger_listen(self):
        """Externally trigger listening."""
        LOG.debug('Listen triggered from external source.')
        self._listen_triggered = True

    def _wait_until_wake_word(self, source, sec_per_buffer, emitter):
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

        # These are frames immediately after wake word is detected
        # that we want to keep to send to STT
        ww_frames = deque(maxlen=7)

        while not said_wake_word and not self._stop_signaled:
            if self._skip_wake_word():
                break
            chunk = self.record_sound_chunk(source)
            ww_frames.append(chunk)

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
                self.write_mic_level(energy, source)
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

                # Save positive wake words as appropriate
                if said_wake_word:
                    SessionManager.touch()
                    payload = {
                        'utterance': self.wake_word_name,
                        'session': SessionManager.get().session_id,
                    }
                    emitter.emit("recognizer_loop:wakeword", payload)

                    audio = None
                    mtd = None
                    if self.save_wake_words:
                        # Save wake word locally
                        audio = self._create_audio_data(byte_data, source)
                        mtd = self._compile_metadata()
                        module = self.wake_word_recognizer.__class__.__name__

                        fn = join(
                            self.saved_wake_words_dir,
                            '_'.join(str(mtd[k]) for k in sorted(mtd)) + '.wav'
                        )
                        with open(fn, 'wb') as f:
                            f.write(audio.get_wav_data())

                    if self.config['opt_in'] and not self.upload_disabled:
                        # Upload wake word for opt_in people
                        Thread(
                            target=self._upload_wake_word, daemon=True,
                            args=[audio or
                                  self._create_audio_data(byte_data, source),
                                  mtd or self._compile_metadata()]
                        ).start()
        return ww_frames

    @staticmethod
    def _create_audio_data(raw_data, source):
        """
        Constructs an AudioData instance with the same parameters
        as the source and the specified frame_data
        """
        return AudioData(raw_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)

    def listen(self, source, emitter, stream=None):
        """Listens for chunks of audio that Mycroft should perform STT on.

        This will listen continuously for a wake-up-word, then return the
        audio chunk containing the spoken phrase that comes immediately
        afterwards.

        Args:
            source (AudioSource):  Source producing the audio chunks
            emitter (EventEmitter): Emitter for notifications of when recording
                                    begins and ends.
            stream (AudioStreamHandler): Stream target that will receive chunks
                                         of the utterance audio while it is
                                         being recorded

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
        ww_frames = self._wait_until_wake_word(source, sec_per_buffer, emitter)

        self._listen_triggered = False
        if self._stop_signaled:
            return

        LOG.debug("Recording...")
        # If enabled, play a wave file with a short sound to audibly
        # indicate recording has begun.
        if self.config.get('confirm_listening'):
            audio_file = resolve_resource_file(
                self.config.get('sounds').get('start_listening'))
            if audio_file:
                source.mute()
                play_wav(audio_file).wait()
                source.unmute()
                # Clear frames from wakeword detctions since they're
                # irrelevant after mute - play wav - unmute sequence
                ww_frames = None

        # Notify system of recording start
        emitter.emit("recognizer_loop:record_begin")

        frame_data = self._record_phrase(
            source,
            sec_per_buffer,
            stream,
            ww_frames
        )
        audio_data = self._create_audio_data(frame_data, source)
        emitter.emit("recognizer_loop:record_end")
        if self.save_utterances:
            LOG.info("Recording utterance")
            stamp = str(datetime.datetime.now())
            filename = "/{}/{}.wav".format(
                self.saved_utterances_dir,
                stamp
            )
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
