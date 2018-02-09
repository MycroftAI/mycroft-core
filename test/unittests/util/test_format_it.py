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
import datetime

from mycroft.util.format import nice_number
from mycroft.util.format import nice_time
from mycroft.util.format import pronounce_number

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


# def pronounce_number(number, lang="it-it", places=2):
class TestPronounceNumber(unittest.TestCase):
    def test_convert_int(self):
        self.assertEqual(pronounce_number(0, lang="it"), "zero")
        self.assertEqual(pronounce_number(1, lang="it"), "uno")
        self.assertEqual(pronounce_number(10, lang="it"), "dieci")
        self.assertEqual(pronounce_number(15, lang="it"), "quindici")
        self.assertEqual(pronounce_number(21, lang="it"), "ventuno")
        self.assertEqual(pronounce_number(27, lang="it"), "ventisette")
        self.assertEqual(pronounce_number(30, lang="it"), "trenta")
        self.assertEqual(pronounce_number(83, lang="it"), "ottantatre")

    def test_convert_negative_int(self):
        self.assertEqual(pronounce_number(-1, lang="it"), "meno uno")
        self.assertEqual(pronounce_number(-10, lang="it"), "meno dieci")
        self.assertEqual(pronounce_number(-15, lang="it"), "meno quindici")
        self.assertEqual(pronounce_number(-21, lang="it"), "meno ventuno")
        self.assertEqual(pronounce_number(-27, lang="it"), "meno ventisette")
        self.assertEqual(pronounce_number(-30, lang="it"), "meno trenta")
        self.assertEqual(pronounce_number(-83, lang="it"), "meno ottantatre")

    def test_convert_decimals(self):
        self.assertEqual(pronounce_number(1.234, lang="it"),
                         "uno virgola due tre")
        self.assertEqual(pronounce_number(21.234, lang="it"),
                         "ventuno virgola due tre")
        self.assertEqual(pronounce_number(21.234, lang="it", places=1),
                         "ventuno virgola due")
        self.assertEqual(pronounce_number(21.234, lang="it", places=0),
                         "ventuno")
        self.assertEqual(pronounce_number(21.234, lang="it", places=3),
                         "ventuno virgola due tre quattro")
        self.assertEqual(pronounce_number(21.234, lang="it", places=4),
                         "ventuno virgola due tre quattro")
        self.assertEqual(pronounce_number(21.234, lang="it", places=5),
                         "ventuno virgola due tre quattro")
        self.assertEqual(pronounce_number(-21.234, lang="it"),
                         "meno ventuno virgola due tre")
        self.assertEqual(pronounce_number(-21.234, lang="it", places=1),
                         "meno ventuno virgola due")
        self.assertEqual(pronounce_number(-21.234, lang="it", places=0),
                         "meno ventuno")
        self.assertEqual(pronounce_number(-21.234, lang="it", places=3),
                         "meno ventuno virgola due tre quattro")
        self.assertEqual(pronounce_number(-21.234, lang="it", places=4),
                         "meno ventuno virgola due tre quattro")
        self.assertEqual(pronounce_number(-21.234, lang="it", places=5),
                         "meno ventuno virgola due tre quattro")


# def nice_time(dt, lang="it-it", speech=True, use_24hour=False,
#              use_ampm=False):
class TestNiceDateFormat(unittest.TestCase):
    def test_convert_times(self):
        dt = datetime.datetime(2017, 1, 31,
                               13, 22, 3)

        # Verify defaults haven't changed
        self.assertEqual(nice_time(dt, lang="it-it"),
                         nice_time(dt, "it-it", True, False, False))

        self.assertEqual(nice_time(dt, lang="it"),
                         "una e ventidue")
        self.assertEqual(nice_time(dt, lang="it", use_ampm=True),
                         "una e ventidue del pomeriggio")
        self.assertEqual(nice_time(dt, lang="it", speech=False), "1:22")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_ampm=True), "1:22 PM")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_24hour=True), "13:22")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_24hour=True, use_ampm=True), "13:22")
        self.assertEqual(nice_time(dt, lang="it", use_24hour=True,
                                   use_ampm=True), "tredici e ventidue")
        self.assertEqual(nice_time(dt, lang="it", use_24hour=True,
                                   use_ampm=False), "tredici e ventidue")

        dt = datetime.datetime(2017, 1, 31,
                               13, 0, 3)
        self.assertEqual(nice_time(dt, lang="it"),
                         "una in punto")
        self.assertEqual(nice_time(dt, lang="it", use_ampm=True),
                         "una del pomeriggio")
        self.assertEqual(nice_time(dt, lang="it", speech=False),
                         "1:00")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_ampm=True), "1:00 PM")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_24hour=True), "13:00")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_24hour=True, use_ampm=True), "13:00")
        self.assertEqual(nice_time(dt, lang="it", use_24hour=True,
                                   use_ampm=True), "tredici e zerozero")
        self.assertEqual(nice_time(dt, lang="it", use_24hour=True,
                                   use_ampm=False), "tredici e zerozero")

        dt = datetime.datetime(2017, 1, 31,
                               13, 2, 3)
        self.assertEqual(nice_time(dt, lang="it", use_24hour=True),
                         "tredici e zero due")
        self.assertEqual(nice_time(dt, lang="it", use_ampm=True),
                         "una e zero due del pomeriggio")
        self.assertEqual(nice_time(dt, lang="it", speech=False),
                         "1:02")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_ampm=True), "1:02 PM")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_24hour=True), "13:02")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_24hour=True, use_ampm=True), "13:02")
        self.assertEqual(nice_time(dt, lang="it", use_24hour=True,
                                   use_ampm=True), "tredici e zero due")
        self.assertEqual(nice_time(dt, lang="it", use_24hour=True,
                                   use_ampm=False), "tredici e zero due")

        dt = datetime.datetime(2017, 1, 31,
                               0, 2, 3)
        self.assertEqual(nice_time(dt, lang="it"),
                         "mezzanotte e zero due")
        self.assertEqual(nice_time(dt, lang="it", use_ampm=True),
                         "mezzanotte e zero due")
        self.assertEqual(nice_time(dt, lang="it", speech=False),
                         "12:02")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_ampm=True), "12:02 AM")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_24hour=True), "00:02")
        self.assertEqual(nice_time(dt, lang="it", speech=False,
                                   use_24hour=True,
                                   use_ampm=True), "00:02")
        self.assertEqual(nice_time(dt, lang="it", use_24hour=True,
                                   use_ampm=True), "zerozero e zero due")
        self.assertEqual(nice_time(dt, lang="it", use_24hour=True,
                                   use_ampm=False), "zerozero e zero due")


if __name__ == "__main__":
    unittest.main()
