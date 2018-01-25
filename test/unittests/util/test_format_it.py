# -*- coding: utf-8 -*-
#
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

from mycroft.util.format import nice_number

NUMBERS_FIXTURE_IT = {
    1.435634: '1.436',
    2: '2',
    5.0: '5',
    0.027: '0.027',
    0.5: 'un mezzo',
    1.333: '1 e un terzo',
    2.666: '2 e 2 terzi',
    0.25: 'un quarto',
    1.25: '1 e un quarto',
    0.75: '3 quarti',
    1.75: '1 e 3 quarti',
    3.4: '3 e 2 quinti',
    16.8333: '16 e 5 sesti',
    12.5714: '12 e 4 settimi',
    9.625: '9 e 5 ottavi',
    6.777: '6 e 7 noni',
    3.1: '3 e un decimo',
    2.272: '2 e 3 undicesimi',
    5.583: '5 e 7 dodicesimi',
    8.384: '8 e 5 tredicesimi',
    0.071: 'un quattordicesimo',
    6.466: '6 e 7 quindicesimi',
    8.312: '8 e 5 sedicesimi',
    2.176: '2 e 3 diciassettesimi',
    200.722: '200 e 13 diciottesimi',
    7.421: '7 e 8 diciannovesimi',
    0.05: 'un ventesimo'
}


class TestNiceNumberFormat(unittest.TestCase):
    def test_convert_float_to_nice_number_it(self):
        for number, number_str in NUMBERS_FIXTURE_IT.items():
            self.assertEqual(nice_number(number, lang="it-it"),
                             number_str,
                             'should format {} as {} and not {}'.format(
                                 number, number_str, nice_number(
                                     number, lang="it-it")))


if __name__ == "__main__":
    unittest.main()
