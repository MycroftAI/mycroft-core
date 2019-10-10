# -*- coding: utf-8 -*-
#
# Copyright 2019 Mycroft AI Inc.
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
from mycroft.util.lang.format_common import convert_to_mixed_fraction as cmf


class TestMixedFraction(unittest.TestCase):
    def test_convert_to_fraction(self):
        self.assertEqual(cmf(8), (8, 0, 1))
        self.assertEqual(cmf(8.00001), (8, 0, 1))
        self.assertEqual(cmf(8.5), (8, 1, 2))
        self.assertEqual(cmf(8.587465135), None)
        self.assertEqual(cmf(8.587465135, range(1, 101)), (8, 47, 80))
