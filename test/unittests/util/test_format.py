# -*- coding: iso-8859-15 -*-
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


numbers_fixture = {
    1.435634: '1.436',
    2: '2',
    5.0: '5',
    0.027: '0.027',
    0.5: 'a half',
    1.333: '1 and a third',
    2.666: '2 and 2 thirds',
    0.25: 'a forth',
    1.25: '1 and a forth',
    0.75: '3 forths',
    1.75: '1 and 3 forths',
    3.4: '3 and 2 fifths',
    16.8333: '16 and 5 sixths',
    12.5714: '12 and 4 sevenths',
    9.625: '9 and 5 eigths',
    6.777: '6 and 7 ninths',
    3.1: '3 and a tenth',
    2.272: '2 and 3 elevenths',
    5.583: '5 and 7 twelveths',
    8.384: '8 and 5 thirteenths',
    0.071: 'a fourteenth',
    6.466: '6 and 7 fifteenths',
    8.312: '8 and 5 sixteenths',
    2.176: '2 and 3 seventeenths',
    200.722: '200 and 13 eighteenths',
    7.421: '7 and 8 nineteenths',
    0.05: 'a twentyith'
}


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


class TestNieceNumberFormat(unittest.TestCase):
    def test_convert_float_to_nice_number(self):
        for number, number_str in numbers_fixture.items():
            self.assertEqual(nice_number(number), number_str,
                             'should format {} as {} and not {}'.format(
                                 number, number_str, nice_number(number)))

    def test_specify_denominator(self):
        self.assertEqual(nice_number(5.5, denominators=[1, 2, 3]),
                         '5 and a half',
                         'should format 5.5 as 5 and a half not {}'.format(
                             nice_number(5.5, denominators=[1, 2, 3])))
        self.assertEqual(nice_number(2.333, denominators=[1, 2]),
                         '2.333',
                         'should format 2.333 as 2.333 not {}'.format(
                             nice_number(2.333, denominators=[1, 2])))

    def test_no_speech(self):
        self.assertEqual(nice_number(6.777, speech=False),
                         '6 7/9',
                         'should format 6.777 as 6 7/9 not {}'.format(
                             nice_number(6.777, speech=False)))
        self.assertEqual(nice_number(6.0, speech=False),
                         '6',
                         'should format 6.0 as 6 not {}'.format(
                             nice_number(6.0, speech=False)))

    def test_different_language(self):
        self.assertEqual(nice_number(5.5, lang="es-us"), '5.5',
                         'should format 5.5 as 5.5 not {}'.format(
                             nice_number(5.5, lang="es-us")))

    def test_convert_float_to_nice_number_it(self):
        for number, number_str in NUMBERS_FIXTURE_IT.items():
            self.assertEqual(nice_number(number, lang="it-it"),
                             number_str,
                             'should format {} as {} and not {}'.format(
                                 number, number_str, nice_number(
                                     number, lang="it-it")))


if __name__ == "__main__":
    unittest.main()
