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

from collections import deque, namedtuple
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

from .data_structures import RollingMean, CyclicAudioBuffer


WakeWordData = namedtuple('WakeWordData',
                          ['audio', 'found', 'stopped', 'end_audio'])


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

    def duration_to_bytes(self, sec):
        """Converts a duration in seconds to number of recorded bytes.

        Arguments:
            sec: number of seconds

        Returns:
            (int) equivalent number of bytes recorded by this Mic
        """
        return int(sec * self.SAMPLE_RATE) * self.SAMPLE_WIDTH


def get_silence(num_bytes):
    return b'\0' * num_bytes


class NoiseTracker:
    """Noise tracker, used to deterimine if an audio utterance is complete.

    The current implementation expects a number of loud chunks (not necessary
    in one continous sequence) followed by a short period of continous quiet
    audio data to be considered complete.

    Arguments:
        minimum (int): lower noise level will be threshold for "quiet" level
        maximum (int): ceiling of noise level
        sec_per_buffer (float): the length of each buffer used when updating
                                the tracker
        loud_time_limit (float): time in seconds of low noise to be considered
                                 a complete sentence
        silence_time_limit (float): time limit for silence to abort sentence
        silence_after_loud (float): time of silence to finalize the sentence.
                                    default 0.25 seconds.
    """
    def __init__(self, minimum, maximum, sec_per_buffer, loud_time_limit,
                 silence_time_limit, silence_after_loud_time=0.25):
        self.min_level = minimum
        self.max_level = maximum
        self.sec_per_buffer = sec_per_buffer

        self.num_loud_chunks = 0
        self.level = 0

        # Smallest number of loud chunks required to return loud enough
        self.min_loud_chunks = int(loud_time_limit / sec_per_buffer)

        self.max_silence_duration = silence_time_limit
        self.silence_duration = 0

        # time of quite period after long enough loud data to consider the
        # sentence complete
        self.silence_after_loud = silence_after_loud_time

        # Constants
        self.increase_multiplier = 200
        self.decrease_multiplier = 100

    def _increase_noise(self):
        """Bumps the current level.

        Modifies the noise level with a factor depending in the buffer length.
        """
        if self.level < self.max_level:
            self.level += self.increase_multiplier * self.sec_per_buffer

    def _decrease_noise(self):
        """Decrease the current level.

        Modifies the noise level with a factor depending in the buffer length.
        """
        if self.level > self.min_level:
            self.level -= self.decrease_multiplier * self.sec_per_buffer

    def update(self, is_loud):
        """Update the tracking. with either a loud chunk or a quiet chunk.

        Arguments:
            is_loud: True if a loud chunk should be registered
                     False if a quiet chunk should be registered
        """
        if is_loud:
            self._increase_noise()
            self.num_loud_chunks += 1
        else:
            self._decrease_noise()
        # Update duration of energy under the threshold level
        if self._quiet_enough():
            self.silence_duration += self.sec_per_buffer
        else:  # Reset silence duration
            self.silence_duration = 0

    def _loud_enough(self):
        """Check if the noise loudness criteria is fulfilled.

        The noise is considered loud enough if it's been over the threshold
        for a certain number of chunks (accumulated, not in a row).
        """
        return self.num_loud_chunks > self.min_loud_chunks

    def _quiet_enough(self):
        """Check if the noise quietness criteria is fulfilled.

        The quiet level is instant and will return True if the level is lower
        or equal to the minimum noise level.
        """
        return self.level <= self.min_level

    def recording_complete(self):
        """Has the end creteria for the recording been met.

        If the noise level has decresed from a loud level to a low level
        the user has stopped speaking.

        Alternatively if a lot of silence was recorded without detecting
        a loud enough phrase.
        """
        too_much_silence = (self.silence_duration > self.max_silence_duration)
        if too_much_silence:
            LOG.debug('Too much silence recorded without start of sentence '
                      'detected')
        return ((self._quiet_enough() and
                 self.silence_duration > self.silence_after_loud) and
                (self._loud_enough() or too_much_silence))


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

        super().__init__()
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

        self.mic_level_file = os.path.join(get_ipc_directory(), "mic_level")

        # Signal statuses
        self._stop_signaled = False
        self._listen_triggered = False

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
        noise_tracker = NoiseTracker(0, 25, sec_per_buffer,
                                     self.MIN_LOUD_SEC_PER_PHRASE,
                                     self.recording_timeout_with_silence)

        # Maximum number of chunks to record before timing out
        max_chunks = int(self.recording_timeout / sec_per_buffer)
        num_chunks = 0

        # bytearray to store audio in, initialized with a single sample of
        # silence.
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
            noise_tracker.update(is_loud)
            if not is_loud:
                self._adjust_threshold(energy, sec_per_buffer)

            # The phrase is complete if the noise_tracker end of sentence
            # criteria is met or if the  top-button is pressed
            phrase_complete = (noise_tracker.recording_complete() or
                               check_for_signal('buttonPress'))

            # Periodically write the energy level to the mic level file.
            if num_chunks % 10 == 0:
                self.write_mic_level(energy, source)

        return byte_data

    def write_mic_level(self, energy, source):
        with open(self.mic_level_file, 'w') as f:
            f.write('Energy:  cur={} thresh={:.3f} muted={}'.format(
                energy,
                self.energy_threshold,
                int(source.muted)
                )
            )

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
        """Signal stop and exit waiting state."""
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

    def _upload_wakeword(self, audio, metadata):
        """Upload the wakeword in a background thread."""
        def upload(audio, metadata):
            requests.post(self.upload_url,
                          files={'audio': BytesIO(audio.get_wav_data()),
                                 'metadata': StringIO(json.dumps(metadata))})

        Thread(target=upload, daemon=True, args=(audio, metadata)).start()

    def _send_wakeword_info(self, emitter):
        """Send messagebus message indicating that a wakeword was received.

        Arguments:
            emitter: bus emitter to send information on.
        """
        SessionManager.touch()
        payload = {'utterance': self.wake_word_name,
                   'session': SessionManager.get().session_id}
        emitter.emit("recognizer_loop:wakeword", payload)

    def _write_wakeword_to_disk(self, audio, metadata):
        """Write wakeword to disk.

        Arguments:
            audio: Audio data to write
            metadata: List of metadata about the captured wakeword
        """
        filename = join(self.saved_wake_words_dir,
                        '_'.join(str(metadata[k]) for k in sorted(metadata)) +
                        '.wav')
        with open(filename, 'wb') as f:
            f.write(audio.get_wav_data())

    def _handle_wakeword_found(self, audio_data, source):
        """Perform actions to be triggered after a wakeword is found.

        This includes: emit event on messagebus that a wakeword is heard,
        store wakeword to disk if configured and sending the wakeword data
        to the cloud in case the user has opted into the data sharing.
        """
        # Save and upload positive wake words as appropriate
        upload_allowed = (self.config['opt_in'] and not self.upload_disabled)
        if (self.save_wake_words or upload_allowed):
            audio = self._create_audio_data(audio_data, source)
            metadata = self._compile_metadata()
            if self.save_wake_words:
                # Save wake word locally
                self._write_wakeword_to_disk(audio, metadata)
            # Upload wake word for opt_in people
            if upload_allowed:
                self._upload_wakeword(audio, metadata)

    def _wait_until_wake_word(self, source, sec_per_buffer):
        """Listen continuously on source until a wake word is spoken

        Arguments:
            source (AudioSource):  Source producing the audio chunks
            sec_per_buffer (float):  Fractional number of seconds in each chunk
        """

        # The maximum audio in seconds to keep for transcribing a phrase
        # The wake word must fit in this time
        ww_duration = self.wake_word_recognizer.expected_duration
        ww_test_duration = max(3, ww_duration)

        mic_write_counter = 0
        num_silent_bytes = int(self.SILENCE_SEC * source.SAMPLE_RATE *
                               source.SAMPLE_WIDTH)

        silence = get_silence(num_silent_bytes)

        # Max bytes for byte_data before audio is removed from the front
        max_size = source.duration_to_bytes(ww_duration)
        test_size = source.duration_to_bytes(ww_test_duration)
        audio_buffer = CyclicAudioBuffer(max_size, silence)

        buffers_per_check = self.SEC_BETWEEN_WW_CHECKS / sec_per_buffer
        buffers_since_check = 0.0

        # Rolling buffer to track the audio energy (loudness) heard on
        # the source recently.  An average audio energy is maintained
        # based on these levels.
        average_samples = int(5 / sec_per_buffer)  # average over last 5 secs
        audio_mean = RollingMean(average_samples)

        # These are frames immediately after wake word is detected
        # that we want to keep to send to STT
        ww_frames = deque(maxlen=7)

        said_wake_word = False
        while (not said_wake_word and not self._stop_signaled and
               not self._skip_wake_word()):
            chunk = self.record_sound_chunk(source)
            audio_buffer.append(chunk)
            ww_frames.append(chunk)

            energy = self.calc_energy(chunk, source.SAMPLE_WIDTH)
            audio_mean.append_sample(energy)

            if energy < self.energy_threshold * self.multiplier:
                self._adjust_threshold(energy, sec_per_buffer)
            # maintain the threshold using average
            if self.energy_threshold < energy < audio_mean.value * 1.5:
                # bump the threshold to just above this value
                self.energy_threshold = energy * 1.2

            # Periodically output energy level stats. This can be used to
            # visualize the microphone input, e.g. a needle on a meter.
            if mic_write_counter % 3:
                self.write_mic_level(energy, source)
            mic_write_counter += 1

            buffers_since_check += 1.0
            # Send chunk to wake_word_recognizer
            self.wake_word_recognizer.update(chunk)

            if buffers_since_check > buffers_per_check:
                buffers_since_check -= buffers_per_check
                audio_data = audio_buffer.get_last(test_size) + silence
                said_wake_word = \
                    self.wake_word_recognizer.found_wake_word(audio_data)

        self._listen_triggered = False
        return WakeWordData(audio_data, said_wake_word,
                            self._stop_signaled, ww_frames)

    @staticmethod
    def _create_audio_data(raw_data, source):
        """
        Constructs an AudioData instance with the same parameters
        as the source and the specified frame_data
        """
        return AudioData(raw_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)

    def mute_and_confirm_listening(self, source):
        audio_file = resolve_resource_file(
            self.config.get('sounds').get('start_listening'))
        if audio_file:
            source.mute()
            play_wav(audio_file).wait()
            source.unmute()
            return True
        else:
            return False

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
        ww_data = self._wait_until_wake_word(source, sec_per_buffer)

        ww_frames = None
        if ww_data.found:
            # If the wakeword was heard send it
            self._send_wakeword_info(emitter)
            self._handle_wakeword_found(ww_data.audio, source)
            ww_frames = ww_data.end_audio
        if ww_data.stopped:
            # If the waiting returned from a stop signal
            return

        LOG.debug("Recording...")
        # If enabled, play a wave file with a short sound to audibly
        # indicate recording has begun.
        if self.config.get('confirm_listening'):
            if self.mute_and_confirm_listening(source):
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
