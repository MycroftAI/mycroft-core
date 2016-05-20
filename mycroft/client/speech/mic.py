import collections
import math
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


class Recognizer(speech_recognition.Recognizer):
    def __init__(self):
        speech_recognition.Recognizer.__init__(self)
        self.max_audio_length_sec = 30

    def listen(self, source, timeout=None):
        """
        Records a single phrase from ``source`` (an ``AudioSource`` instance)
        into an ``AudioData`` instance, which it returns.

        This is done by waiting until the audio has an energy above
        ``recognizer_instance.energy_threshold`` (the user has started
        speaking), and then recording until it encounters
        ``recognizer_instance.pause_threshold`` seconds of non-speaking or
        there is no more audio input. The ending silence is not included.

        The ``timeout`` parameter is the maximum number of seconds that it
        will wait for a phrase to start before giving up and throwing an
        ``speech_recognition.WaitTimeoutError`` exception. If ``timeout`` is
        ``None``, it will wait indefinitely.
        """
        assert isinstance(source, AudioSource), \
            "Source must be an audio source"
        assert self.pause_threshold >= self.non_speaking_duration >= 0

        seconds_per_buffer = (source.CHUNK + 0.0) / source.SAMPLE_RATE
        # number of buffers of non-speaking audio before the phrase is
        # complete
        pause_buffer_count = int(
            math.ceil(self.pause_threshold / seconds_per_buffer))
        # minimum number of buffers of speaking audio before we consider the
        # speaking audio a phrase
        phrase_buffer_count = int(math.ceil(self.phrase_threshold /
                                            seconds_per_buffer))
        # maximum number of buffers of non-speaking audio to retain before and
        # after
        non_speaking_buffer_count = int(math.ceil(self.non_speaking_duration /
                                                  seconds_per_buffer))

        # read audio input for phrases until there is a phrase that is long
        # enough
        elapsed_time = 0  # number of seconds of audio read
        while True:
            frames = collections.deque()

            # store audio input until the phrase starts
            while True:
                elapsed_time += seconds_per_buffer
                # handle timeout if specified
                if timeout and elapsed_time > timeout:
                    raise WaitTimeoutError("listening timed out")

                buffer = source.stream.read(source.CHUNK)
                if len(buffer) == 0:
                    break  # reached end of the stream
                frames.append(buffer)
                # ensure we only keep the needed amount of non-speaking buffers
                if len(frames) > non_speaking_buffer_count:
                    frames.popleft()

                # detect whether speaking has started on audio input
                # energy of the audio signal
                energy = audioop.rms(buffer, source.SAMPLE_WIDTH)
                if energy > self.energy_threshold:
                    break

                # dynamically adjust the energy threshold using assymmetric
                # weighted average
                # do not adjust dynamic energy level for this sample if it is
                # muted audio (energy == 0)
                self.adjust_energy_threshold(energy, seconds_per_buffer)
            # read audio input until the phrase ends
            pause_count, phrase_count = 0, 0
            while True:
                elapsed_time += seconds_per_buffer

                buffer = source.stream.read(source.CHUNK)
                if len(buffer) == 0:
                    break  # reached end of the stream
                frames.append(buffer)
                phrase_count += 1

                # check if speaking has stopped for longer than the pause
                # threshold on the audio input
                # energy of the audio signal
                energy = audioop.rms(buffer, source.SAMPLE_WIDTH)
                if energy > self.energy_threshold:
                    pause_count = 0
                else:
                    pause_count += 1
                if pause_count > pause_buffer_count:  # end of the phrase
                    break

                if (len(frames) * seconds_per_buffer >=
                        self.max_audio_length_sec):
                    # if we hit the end of the audio length, readjust
                    # energy_threshold
                    for frame in frames:
                        energy = audioop.rms(frame, source.SAMPLE_WIDTH)
                        self.adjust_energy_threshold(
                            energy, seconds_per_buffer)
                    break

            # check how long the detected phrase is, and retry listening if
            # the phrase is too short
            phrase_count -= pause_count
            if phrase_count >= phrase_buffer_count:
                break  # phrase is long enough, stop listening

        # obtain frame data
        for i in range(pause_count - non_speaking_buffer_count):
            frames.pop()  # remove extra non-speaking frames at the end
        frame_data = b"".join(list(frames))

        return AudioData(frame_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)

    def adjust_energy_threshold(self, energy, seconds_per_buffer):
        if self.dynamic_energy_threshold and energy > 0:
            # account for different chunk sizes and rates
            damping = (
                self.dynamic_energy_adjustment_damping ** seconds_per_buffer)
            target_energy = energy * self.dynamic_energy_ratio
            self.energy_threshold = (
                self.energy_threshold * damping +
                target_energy * (1 - damping))
