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
