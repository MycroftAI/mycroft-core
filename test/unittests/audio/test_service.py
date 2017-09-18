import unittest

from os.path import dirname, join, abspath

import mycroft.audio.main as audio_service

"""
    Tests for service loader
"""


class MockEmitter(object):
    def __init__(self):
        self.reset()

    def emit(self, message):
        self.types.append(message.type)
        self.results.append(message.data)

    def get_types(self):
        return self.types

    def get_results(self):
        return self.results

    def reset(self):
        self.types = []
        self.results = []


class TestService(unittest.TestCase):
    emitter = MockEmitter()
    service_path = abspath(join(dirname(__file__), 'services'))

    def setUp(self):
        pass

    def test_load(self):
        services = audio_service.load_services({}, TestService.emitter,
                                               TestService.service_path)
        self.assertEquals(len(services), 1)


if __name__ == "__main__":
    unittest.main()
