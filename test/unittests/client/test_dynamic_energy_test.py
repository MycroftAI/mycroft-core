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
from unittest import TestCase, mock

from speech_recognition import AudioSource

from mycroft.client.speech.mic import ResponsiveRecognizer


class MockStream:
    def __init__(self):
        self.chunks = []

    def inject(self, chunk):
        self.chunks.append(chunk)

    def read(self, chunk_size):
        result = self.chunks[0]
        if len(self.chunks) > 1:
            self.chunks = self.chunks[1:]
        return result


class MockSource(AudioSource):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def __init__(self, stream=None):
        self.stream = stream if stream else MockStream()
        self.CHUNK = 1024
        self.SAMPLE_RATE = 16000
        self.SAMPLE_WIDTH = 2


class MockHotwordEngine(mock.Mock):
    def __init__(self, *arg, **kwarg):
        super().__init__(*arg, **kwarg)
        self.num_phonemes = 10


class DynamicEnergytest(TestCase):
    def testMaxAudioWithBaselineShift(self):
        low_base = b"\x10\x00\x01\x00" * 100
        higher_base = b"\x01\x00\x00\x01" * 100

        source = MockSource()

        for i in range(100):
            source.stream.inject(low_base)

        source.stream.inject(higher_base)
        recognizer = ResponsiveRecognizer(MockHotwordEngine())

        sec_per_buffer = float(source.CHUNK) / (source.SAMPLE_RATE *
                                                source.SAMPLE_WIDTH)

        test_seconds = 30.0
        while test_seconds > 0:
            test_seconds -= sec_per_buffer
            data = source.stream.read(source.CHUNK)
            energy = recognizer.calc_energy(data, source.SAMPLE_WIDTH)
            recognizer._adjust_threshold(energy, sec_per_buffer)

        higher_base_energy = audioop.rms(higher_base, source.SAMPLE_WIDTH)
        # after recalibration (because of max audio length) new threshold
        # should be >= 1.5 * higher_base_energy
        delta_below_threshold = (
            recognizer.energy_threshold - higher_base_energy)
        min_delta = higher_base_energy * .5
        assert abs(delta_below_threshold - min_delta) < 1
