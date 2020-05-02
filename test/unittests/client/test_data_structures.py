# Copyright 2020 Mycroft AI Inc.
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
from unittest import TestCase

from mycroft.client.speech.data_structures import (RollingMean,
                                                   CyclicAudioBuffer)


class TestRollingMean(TestCase):
    def test_before_rolling(self):
        mean = RollingMean(10)
        for i in range(5):
            mean.append_sample(i)

        self.assertEqual(mean.value, 2)
        for i in range(5):
            mean.append_sample(i)
        self.assertEqual(mean.value, 2)

    def test_during_rolling(self):
        mean = RollingMean(10)
        for _ in range(10):
            mean.append_sample(5)
        self.assertEqual(mean.value, 5)

        for _ in range(5):
            mean.append_sample(1)
        # Values should now be 5, 5, 5, 5, 5, 1, 1, 1, 1, 1
        self.assertAlmostEqual(mean.value, 3)

        for _ in range(5):
            mean.append_sample(2)
        # Values should now be 1, 1, 1, 1, 1, 2, 2, 2, 2, 2
        self.assertAlmostEqual(mean.value, 1.5)


class TestCyclicBuffer(TestCase):
    def test_init(self):
        buff = CyclicAudioBuffer(16, b'abc')
        self.assertEqual(buff.get(), b'abc')
        self.assertEqual(len(buff), 3)

    def test_init_larger_inital_data(self):
        size = 16
        buff = CyclicAudioBuffer(size, b'a' * (size + 3))
        self.assertEqual(buff.get(), b'a' * size)

    def test_append_with_room_left(self):
        buff = CyclicAudioBuffer(16, b'abc')
        buff.append(b'def')
        self.assertEqual(buff.get(), b'abcdef')

    def test_append_with_full(self):
        buff = CyclicAudioBuffer(3, b'abc')
        buff.append(b'de')
        self.assertEqual(buff.get(), b'cde')
        self.assertEqual(len(buff), 3)

    def test_get_last(self):
        buff = CyclicAudioBuffer(3, b'abcdef')
        self.assertEqual(buff.get_last(3), b'def')

    def test_get_item(self):
        buff = CyclicAudioBuffer(6, b'abcdef')
        self.assertEqual(buff[:], b'abcdef')
