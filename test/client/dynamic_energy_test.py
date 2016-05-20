import unittest
import audioop
from speech_recognition import AudioSource
from mycroft.client.speech.mic import Recognizer

__author__ = 'seanfitz'


class MockStream(object):
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


class DynamicEnergytest(unittest.TestCase):
    def setUp(self):
        pass

    def testMaxAudioWithBaselineShift(self):
        low_base = b"".join(["\x10\x00\x01\x00"] * 100)
        higher_base = b"".join(["\x01\x00\x00\x01"] * 100)

        source = MockSource()
        for i in xrange(100):
            source.stream.inject(low_base)

        source.stream.inject(higher_base)
        recognizer = Recognizer()
        recognizer.listen(source)
        higher_base_energy = audioop.rms(higher_base, 2)
        # after recalibration (because of max audio length) new threshold should be >= 1.5 * higher_base_energy
        delta_below_threshold =  recognizer.energy_threshold - higher_base_energy
        min_delta = higher_base_energy * .5
        assert abs(delta_below_threshold - min_delta) < 1