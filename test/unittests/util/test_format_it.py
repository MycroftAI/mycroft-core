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
import sys
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
            self.assertEqual(nice_number(number, lang='it'), number_str,
                             'dovrebbe formattare {} come {} e none {}'.format(
                                 number, number_str, nice_number(
                                     number, lang="it")))

    def test_specify_denominator(self):
        self.assertEqual(nice_number(5.5, denominators=[1, 2, 3],
                                     lang="it"), '5 e un mezzo',
                         'dovrebbe dare 5.5 come 5 e un mezzo non {}'.format(
                             nice_number(5.5, denominators=[1, 2, 3],
                                         lang="it")))
        self.assertEqual(nice_number(2.333, denominators=[1, 2],
                                     lang="it"), '2.333',
                         'dovrebbe dare 2.333 come 2.333 non {}'.format(
                             nice_number(2.333, denominators=[1, 2],
                                         lang="it")))

    def test_no_speech(self):
        self.assertEqual(nice_number(6.777, speech=False, lang="it"),
                         '6 7/9',
                         'dovrebbe formattare 6.777 come 6 7/9 non {}'.format(
                             nice_number(6.777, speech=False)))
        self.assertEqual(nice_number(6.0, speech=False, lang="it"),
                         '6',
                         'dovrebbe formattare 6.0 come 6 non {}'.format(
                             nice_number(6.0, speech=False)))


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

    def test_convert_hundreds(self):
        self.assertEqual(pronounce_number(100, lang="it"), "cento")
        self.assertEqual(pronounce_number(121, lang="it"), "cento ventuno")
        self.assertEqual(pronounce_number(121000, lang="it"),
                         "cento ventunomila")
        self.assertEqual(pronounce_number(666, lang="it"),
                         "seicento sessantasei")
        self.assertEqual(pronounce_number(1456, lang="it"),
                         "mille, quattrocento cinquantasei")
        self.assertEqual(pronounce_number(103254654, lang="it"),
                         "cento tremilioni, duecento "
                         "cinquantaquattromila, seicento "
                         "cinquantaquattro")
        self.assertEqual(pronounce_number(1512457, lang="it"),
                         "un milione, cinquecento dodicimila, "
                         "quattrocento cinquantasette")
        self.assertEqual(pronounce_number(209996, lang="it"),
                         "duecento novemila, novecento novantasei")
        self.assertEqual(pronounce_number(95505896639631893, lang="it"),
                         "novantacinquebiliardi, cinquecento cinquebilioni, "
                         "ottocento novantaseimiliardi, "
                         "seicento trentanovemilioni, seicento "
                         "trentunomila, ottocento novantatre")
        self.assertEqual(pronounce_number(95505896639631893,
                                          short_scale=False, lang="it"),
                         "novantacinquemila cinquecento cinque miliardi, "
                         "ottocento novantaseimila seicento trentanove"
                         " milioni, seicento trentunomila, ottocento"
                         " novantatre")

    def test_convert_scientific_notation(self):
        """
        Test cases for italian text to scientific_notatio

        """
        self.assertEqual(pronounce_number(0, scientific=True,
                                          lang="it"), "zero")
        self.assertEqual(pronounce_number(33, scientific=True,
                                          lang="it"),
                         "tre virgola tre per dieci elevato alla uno")
        self.assertEqual(pronounce_number(299792458, scientific=True,
                                          lang="it"),
                         "due virgola nove nove per dieci elevato alla otto")
        self.assertEqual(pronounce_number(299792458, places=6,
                                          scientific=True, lang="it"),
                         "due virgola nove nove sette nove due cinque "
                         "per dieci elevato alla otto")
        self.assertEqual(pronounce_number(1.672e-27, places=3,
                                          scientific=True, lang="it"),
                         "uno virgola sei sette due per dieci elevato alla "
                         "meno ventisette")
        self.assertEqual(pronounce_number(-33, scientific=True,
                                          lang="it"),
                         "meno tre virgola tre per dieci elevato alla uno")
        self.assertEqual(pronounce_number(-299792458, scientific=True,
                                          lang="it"),
                         "meno due virgola nove nove per dieci elevato"
                         " alla otto")
        self.assertEqual(pronounce_number(-1.672e-27, places=3,
                                          scientific=True, lang="it"),
                         "meno uno virgola sei sette due per dieci elevato"
                         " alla meno ventisette")

    def test_large_numbers(self):
        self.assertEqual(
            pronounce_number(299792458, short_scale=True, lang="it"),
            "duecento novantanovemilioni, settecento "
            "novantaduemila, quattrocento cinquantotto")
        self.assertEqual(
            pronounce_number(299792458, short_scale=False, lang="it"),
            "duecento novantanove milioni, settecento "
            "novantaduemila, quattrocento cinquantotto")
        self.assertEqual(
            pronounce_number(100034000000299792458, short_scale=True,
                             lang="it"),
            "centotrilioni, trentaquattrobiliardi, "
            "duecento novantanovemilioni, settecento "
            "novantaduemila, quattrocento cinquantotto")
        self.assertEqual(
            pronounce_number(100034000000299792458, short_scale=False,
                             lang="it"),
            "cento bilioni, trentaquattromila miliardi, "
            "duecento novantanove milioni, settecento "
            "novantaduemila, quattrocento cinquantotto")
        self.assertEqual(
            pronounce_number(10000000000, short_scale=True, lang="it"),
            "diecimiliardi")
        self.assertEqual(
            pronounce_number(1000000000000, short_scale=True, lang="it"),
            "bilioni")
        self.assertEqual(
            pronounce_number(1000001, short_scale=True, lang="it"),
            "un milione, uno")
        self.assertEqual(
            pronounce_number(1000000000, short_scale=False, lang="it"),
            "un miliardo")
        self.assertEqual(
            pronounce_number(1000000, short_scale=False, lang="it"),
            "un milione")
        self.assertEqual(
            pronounce_number(1000, short_scale=False, lang="it"),
            "mille")
        self.assertEqual(
            pronounce_number(1000900, short_scale=False, lang="it"),
            "uno milioni, novecento")

    def test_convert_times(self):
        dt = datetime.datetime(2017, 1, 31, 13, 22, 3)

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
        # Verifica fasce orarie use_ampm = True
        d_time = datetime.datetime(2017, 1, 31, 8, 22, 3)
        self.assertEqual(nice_time(d_time, lang="it", use_ampm=True),
                         "otto e ventidue della mattina")
        d_time = datetime.datetime(2017, 1, 31, 20, 22, 3)
        self.assertEqual(nice_time(d_time, lang="it", use_ampm=True),
                         "otto e ventidue della sera")
        d_time = datetime.datetime(2017, 1, 31, 23, 22, 3)
        self.assertEqual(nice_time(d_time, lang="it", use_ampm=True),
                         "undici e ventidue della notte")
        d_time = datetime.datetime(2017, 1, 31, 00, 00, 3)
        self.assertEqual(nice_time(d_time, lang="it", use_ampm=True),
                         "mezzanotte")
        d_time = datetime.datetime(2017, 1, 31, 12, 00, 3)
        self.assertEqual(nice_time(d_time, lang="it", use_ampm=True),
                         "mezzogiorno")
        dt = datetime.datetime(2017, 1, 31, 13, 0, 3)
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

        dt = datetime.datetime(2017, 1, 31, 13, 2, 3)
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

        dt = datetime.datetime(2017, 1, 31, 0, 2, 3)
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
        # casi particolari
        d_time = datetime.datetime(2017, 1, 31, 1, 2, 3)
        self.assertEqual(nice_time(d_time, lang="it", use_24hour=True,
                                   use_ampm=True), "una e zero due")
        d_time = datetime.datetime(2017, 1, 31, 2, 2, 3)
        self.assertEqual(nice_time(d_time, lang="it", use_24hour=True,
                                   use_ampm=False), "zero due e zero due")
        d_time = datetime.datetime(2017, 1, 31, 10, 15, 0)
        self.assertEqual(nice_time(d_time, lang="it", use_24hour=False,
                                   use_ampm=False), "dieci e un quarto")
        d_time = datetime.datetime(2017, 1, 31, 22, 45, 0)
        self.assertEqual(nice_time(d_time, lang="it", use_24hour=False,
                                   use_ampm=False), "dieci e tre quarti")

    def test_infinity(self):
        self.assertEqual(pronounce_number(sys.float_info.max * 2,
                                          lang="it"), "infinito")
        self.assertEqual(pronounce_number(float("inf"),
                                          lang="it"), "infinito")
        self.assertEqual(pronounce_number(float("-inf"),
                                          lang="it"), "meno infinito")

if __name__ == "__main__":
    unittest.main()
