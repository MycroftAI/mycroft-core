# Copyright 2022 Mycroft AI Inc.
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
import math
import typing
from collections import deque
from dataclasses import dataclass
from enum import Enum


class SilenceMethod(str, Enum):
    """Method used to determine if an audio frame contains silence.

    Values
    ------
    VAD_ONLY
      Only use webrtcvad

    RATIO_ONLY
      Only use max/current energy ratio threshold

    CURRENT_ONLY
      Only use current energy threshold

    VAD_AND_RATIO
      Use webrtcvad and max/current energy ratio threshold

    VAD_AND_CURRENT
      Use webrtcvad and current energy threshold

    ALL
      Use webrtcvad, max/current energy ratio, and current energy threshold
    """

    VAD_ONLY = "vad_only"
    RATIO_ONLY = "ratio_only"
    CURRENT_ONLY = "current_only"
    VAD_AND_RATIO = "vad_and_ratio"
    VAD_AND_CURRENT = "vad_and_current"
    ALL = "all"


class SilenceResultType(str, Enum):
    SILENCE = "silence"
    SPEECH = "speech"
    TIMEOUT = "timeout"

    PHRASE_START = "phrase_start"
    PHRASE_END = "phrase_end"


@dataclass
class SilenceResult:
    type: SilenceResultType
    energy: float


# -----------------------------------------------------------------------------


class SilenceDetector:
    """Detect speech/silence using Silero VAD.

    Attributes
    ----------
    vad_threshold: float = 0.2
        Value in [0-1], below which is considered silence

    sample_rate: int = 16000
        Sample rate of audio chunks (hertz)

    chunk_size: int = 960
        Must be 30, 60, or 100 ms in duration

    skip_seconds: float = 0
        Seconds of audio to skip before voice command detection starts

    speech_seconds: float = 0.3
        Seconds of speech before voice command has begun

    before_seconds: float = 0.5
        Seconds of audio to keep before voice command has begun

    min_seconds: float = 1.0
        Minimum length of voice command (seconds)

    max_seconds: Optional[float] = 30.0
        Maximum length of voice command before timeout (seconds, None for no timeout)

    silence_seconds: float = 0.5
        Seconds of silence before a voice command has finished

    max_energy: Optional[float] = None
        Maximum denoise energy value (None for dynamic setting from observed audio)

    max_current_ratio_threshold: Optional[float] = None
        Ratio of max/current energy below which audio is considered speech

    current_energy_threshold: Optional[float] = None
        Energy threshold above which audio is considered speech

    silence_method: SilenceMethod = "vad_only"
        Method for deciding if an audio chunk contains silence or speech
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 960,
        skip_seconds: float = 0,
        min_seconds: float = 1,
        max_seconds: typing.Optional[float] = 30,
        speech_seconds: float = 0.3,
        silence_seconds: float = 0.5,
        before_seconds: float = 0.5,
        max_energy: typing.Optional[float] = None,
        max_current_ratio_threshold: typing.Optional[float] = None,
        current_energy_threshold: typing.Optional[float] = None,
        silence_method: SilenceMethod = SilenceMethod.VAD_ONLY,
        plugin: str = None
    ):
        self.sample_rate = sample_rate
        self.sample_width = 2  # 16-bit
        self.sample_channels = 1  # mono
        self.chunk_size = chunk_size
        self.skip_seconds = skip_seconds
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds
        self.speech_seconds = speech_seconds
        self.silence_seconds = silence_seconds
        self.before_seconds = before_seconds

        self.max_energy = max_energy
        self.dynamic_max_energy = max_energy is None
        self.max_current_ratio_threshold = max_current_ratio_threshold
        self.current_energy_threshold = current_energy_threshold
        self.silence_method = silence_method

        # Verify settings
        if self.silence_method in [
            SilenceMethod.VAD_ONLY,
            SilenceMethod.VAD_AND_RATIO,
            SilenceMethod.VAD_AND_CURRENT,
            SilenceMethod.ALL,
        ]:
            self.use_vad = True
        else:
            self.use_vad = False

        if self.silence_method in [
            SilenceMethod.VAD_AND_RATIO,
            SilenceMethod.RATIO_ONLY,
            SilenceMethod.ALL,
        ]:
            self.use_ratio = True
            assert (
                self.max_current_ratio_threshold is not None
            ), "Max/current ratio threshold is required"
        else:
            self.use_ratio = False

        if self.silence_method in [
            SilenceMethod.VAD_AND_CURRENT,
            SilenceMethod.CURRENT_ONLY,
            SilenceMethod.ALL,
        ]:
            self.use_current = True
            assert (
                self.current_energy_threshold is not None
            ), "Current energy threshold is required"
        else:
            self.use_current = False

        # Voice detector
        self.vad = plugin
        if not plugin:
            self.use_vad = False
            if not self.use_current and not self.use_ratio:
                self.use_ratio = True

        self.seconds_per_buffer = (
            self.chunk_size / self.sample_width
        ) / self.sample_rate

        # Store some number of seconds of audio data immediately before voice command starts
        self.before_buffers = int(
            math.ceil(self.before_seconds / self.seconds_per_buffer)
        )

        # Pre-compute values
        self.speech_buffers = int(
            math.ceil(self.speech_seconds / self.seconds_per_buffer)
        )

        self.skip_buffers = int(math.ceil(self.skip_seconds / self.seconds_per_buffer))

        # State
        self.before_phrase_chunks: typing.Deque[bytes] = deque(
            maxlen=self.before_buffers
        )
        self.phrase_buffer: bytes = bytes()

        self.max_buffers: typing.Optional[int] = None
        self.min_phrase_buffers: int = 0
        self.skip_buffers_left: int = 0
        self.speech_buffers_left: int = 0
        self.in_phrase: bool = False
        self.after_phrase: bool = False
        self.silence_buffers: int = 0
        self.current_seconds: float = 0
        self.current_chunk: bytes = bytes()

    def start(self):
        """Begin new voice command."""

        # State
        self.before_phrase_chunks.clear()
        self.phrase_buffer = bytes()

        if self.max_seconds:
            self.max_buffers = int(
                math.ceil(self.max_seconds / self.seconds_per_buffer)
            )
        else:
            self.max_buffers = None

        self.min_phrase_buffers = int(
            math.ceil(self.min_seconds / self.seconds_per_buffer)
        )

        self.speech_buffers_left = self.speech_buffers
        self.skip_buffers_left = self.skip_buffers
        self.in_phrase = False
        self.after_phrase = False
        self.silence_buffers = int(
            math.ceil(self.silence_seconds / self.seconds_per_buffer)
        )

        self.current_seconds: float = 0

        self.current_chunk: bytes = bytes()

    def stop(self) -> bytes:
        """Free any resources and return recorded audio."""
        before_buffer = bytes()
        for before_chunk in self.before_phrase_chunks:
            before_buffer += before_chunk

        audio_data = before_buffer + self.phrase_buffer

        # Clear state
        self.before_phrase_chunks.clear()
        self.phrase_buffer = bytes()
        self.current_chunk = bytes()

        # Return leftover audio
        return audio_data

    def process(self, audio_chunk: bytes) -> SilenceResult:
        """Process a single chunk of audio data."""
        result: typing.Optional[SilenceResult] = None
        is_speech = False
        energy = SilenceDetector.get_debiased_energy(audio_chunk)

        # Add to overall buffer
        self.current_chunk += audio_chunk

        # Process audio in exact chunk(s)
        while len(self.current_chunk) > self.chunk_size:
            # Extract chunk
            chunk = self.current_chunk[: self.chunk_size]
            self.current_chunk = self.current_chunk[self.chunk_size :]

            if self.skip_buffers_left > 0:
                # Skip audio at beginning
                self.skip_buffers_left -= 1
                continue

            if self.in_phrase:
                self.phrase_buffer += chunk
            else:
                self.before_phrase_chunks.append(chunk)

            self.current_seconds += self.seconds_per_buffer

            # Check maximum number of seconds to record
            if self.max_buffers:
                self.max_buffers -= 1
                if self.max_buffers <= 0:
                    # Timeout
                    return SilenceResult(type=SilenceResultType.TIMEOUT, energy=energy)

            # Detect speech in chunk
            is_speech = not self.is_silence(chunk, energy=energy)

            # Handle state changes
            if is_speech and self.speech_buffers_left > 0:
                self.speech_buffers_left -= 1
            elif is_speech and not self.in_phrase:
                # Start of phrase
                result = SilenceResult(
                    type=SilenceResultType.PHRASE_START, energy=energy
                )

                self.in_phrase = True
                self.after_phrase = False
                self.min_phrase_buffers = int(
                    math.ceil(self.min_seconds / self.seconds_per_buffer)
                )
            elif self.in_phrase and (self.min_phrase_buffers > 0):
                # In phrase, before minimum seconds
                self.min_phrase_buffers -= 1
            elif not is_speech:
                # Outside of speech
                if not self.in_phrase:
                    # Reset
                    self.speech_buffers_left = self.speech_buffers
                elif self.after_phrase and (self.silence_buffers > 0):
                    # After phrase, before stop
                    self.silence_buffers -= 1
                elif self.after_phrase and (self.silence_buffers <= 0):
                    # Phrase complete
                    # Merge before/during command audio data
                    before_buffer = bytes()
                    for before_chunk in self.before_phrase_chunks:
                        before_buffer += before_chunk

                    return SilenceResult(
                        type=SilenceResultType.PHRASE_END, energy=energy
                    )
                elif self.in_phrase and (self.min_phrase_buffers <= 0):
                    # Transition to after phrase
                    self.after_phrase = True
                    self.silence_buffers = int(
                        math.ceil(self.silence_seconds / self.seconds_per_buffer)
                    )

        if result is None:
            # Report speech/silence
            result = SilenceResult(
                type=SilenceResultType.SPEECH
                if is_speech
                else SilenceResultType.SILENCE,
                energy=energy,
            )

        return result

    # -------------------------------------------------------------------------

    def is_silence(self, chunk: bytes, energy: typing.Optional[float] = None) -> bool:
        """True if audio chunk contains silence."""
        all_silence = True

        if self.use_vad:
            assert self.vad is not None
            all_silence = all_silence and self.vad.is_silence(chunk)

        if self.use_ratio or self.use_current:
            # Compute debiased energy of audio chunk
            if energy is None:
                energy = SilenceDetector.get_debiased_energy(chunk)

            if self.use_ratio:
                # Ratio of max/current energy compared to threshold
                if self.dynamic_max_energy:
                    # Overwrite max energy
                    if self.max_energy is None:
                        self.max_energy = energy
                    else:
                        self.max_energy = max(energy, self.max_energy)

                assert self.max_energy is not None
                if energy > 0:
                    ratio = self.max_energy / energy
                else:
                    # Not sure what to do here
                    ratio = 0

                assert self.max_current_ratio_threshold is not None
                all_silence = all_silence and (ratio > self.max_current_ratio_threshold)
            elif self.use_current:
                # Current energy compared to threshold
                assert self.current_energy_threshold is not None
                all_silence = all_silence and (energy < self.current_energy_threshold)

        return all_silence

    # -------------------------------------------------------------------------

    @staticmethod
    def get_debiased_energy(audio_data: bytes) -> float:
        """Compute RMS of debiased audio."""
        # Thanks to the speech_recognition library!
        # https://github.com/Uberi/speech_recognition/blob/master/speech_recognition/__init__.py
        energy = -audioop.rms(audio_data, 2)
        energy_bytes = bytes([energy & 0xFF, (energy >> 8) & 0xFF])
        debiased_energy = audioop.rms(
            audioop.add(audio_data, energy_bytes * (len(audio_data) // 2), 2), 2
        )

        # Probably actually audio if > 30
        return debiased_energy
