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
from mycroft.util.lang.format_hu import pronounce_ordinal_hu

# fractions are not capitalized for now
NUMBERS_FIXTURE_HU = {
    1.435634: '1,436',
    2: '2',
    5.0: '5',
    1234567890: '1234567890',
    12345.67890: '12345,679',
    0.027: '0,027',
    0.5: 'fél',
    1.333: '1 egész egy harmad',
    2.666: '2 egész 2 harmad',
    0.25: 'egy negyed',
    1.25: '1 egész egy negyed',
    0.75: '3 negyed',
    1.75: '1 egész 3 negyed',
    3.4: '3 egész 2 ötöd',
    16.8333: '16 egész 5 hatod',
    12.5714: '12 egész 4 heted',
    9.625: '9 egész 5 nyolcad',
    6.777: '6 egész 7 kilenced',
    3.1: '3 egész egy tized',
    2.272: '2 egész 3 tizenegyed',
    5.583: '5 egész 7 tizenketted',
    8.384: '8 egész 5 tizenharmad',
    0.071: 'egy tizennegyed',
    6.466: '6 egész 7 tizenötöd',
    8.312: '8 egész 5 tizenhatod',
    2.176: '2 egész 3 tizenheted',
    200.722: '200 egész 13 tizennyolcad',
    7.421: '7 egész 8 tizenkilenced',
    0.05: 'egy huszad'
}


class TestNiceNumberFormat(unittest.TestCase):
    def test_convert_float_to_nice_number(self):
        for number, number_str in NUMBERS_FIXTURE_HU.items():
            self.assertEqual(nice_number(number, lang="hu-hu"), number_str,
                             'should format {} as {} and not {}'.format(
                                 number, number_str,
                                 nice_number(number, lang="hu-hu")))

    def test_specify_denominator(self):
        self.assertEqual(nice_number(5.5, lang="hu-hu",
                                     denominators=[1, 2, 3]), '5 és fél',
                         'should format 5.5 as 5 és fél not {}'.format(
                             nice_number(5.5, denominators=[1, 2, 3])))
        self.assertEqual(nice_number(2.333, lang="hu-hu", denominators=[1, 2]),
                         '2,333',
                         'should format 2,333 as 2,333 not {}'.format(
                             nice_number(2.333, lang="hu-hu",
                                         denominators=[1, 2])))

    def test_no_speech(self):
        self.assertEqual(nice_number(6.777, speech=False),
                         '6 7/9',
                         'should format 6.777 as 6 7/9 not {}'.format(
                             nice_number(6.777, lang="hu-hu", speech=False)))
        self.assertEqual(nice_number(6.0, speech=False),
                         '6',
                         'should format 6.0 as 6 not {}'.format(
                             nice_number(6.0, lang="hu-hu", speech=False)))


class TestPronounceOrdinal(unittest.TestCase):
    def test_convert_int_hu(self):
        self.assertEqual(pronounce_ordinal_hu(0),
                         "nulladik")
        self.assertEqual(pronounce_ordinal_hu(1),
                         "első")
        self.assertEqual(pronounce_ordinal_hu(3),
                         "harmadik")
        self.assertEqual(pronounce_ordinal_hu(5),
                         "ötödik")
        self.assertEqual(pronounce_ordinal_hu(15),
                         "tizenötödik")
        self.assertEqual(pronounce_ordinal_hu(25),
                         "huszonötödik")
        self.assertEqual(pronounce_ordinal_hu(1000),
                         "ezredik")
        self.assertEqual(pronounce_ordinal_hu(60),
                         "hatvanadik")
        self.assertEqual(pronounce_ordinal_hu(1266),
                         "ezerkétszázhatvanhatodik")
        self.assertEqual(pronounce_ordinal_hu(101),
                         "százegyedik")
        self.assertEqual(pronounce_ordinal_hu(123456),
                         "százhuszonháromezer-négyszázötvenhatodik")
        self.assertEqual(pronounce_ordinal_hu(8000000),
                         "nyolcmilliomodik")


# def pronounce_number(number, lang="hu-hu", places=2):
class TestPronounceNumber(unittest.TestCase):
    def test_convert_int_hu(self):
        self.assertEqual(pronounce_number(123456789123456789, lang="hu-hu"),
                         "százhuszonhárombilliárd-"
                         "négyszázötvenhatbillió-"
                         "hétszáznyolcvankilencmilliárd-"
                         "százhuszonhárommillió-"
                         "négyszázötvenhatezer-"
                         "hétszáznyolcvankilenc")
        self.assertEqual(pronounce_number(1, lang="hu-hu"), "egy")
        self.assertEqual(pronounce_number(10, lang="hu-hu"), "tíz")
        self.assertEqual(pronounce_number(15, lang="hu-hu"), "tizenöt")
        self.assertEqual(pronounce_number(20, lang="hu-hu"), "húsz")
        self.assertEqual(pronounce_number(27, lang="hu-hu"),
                         "huszonhét")
        self.assertEqual(pronounce_number(30, lang="hu-hu"), "harminc")
        self.assertEqual(pronounce_number(33, lang="hu-hu"), "harminchárom")
        self.assertEqual(pronounce_number(71, lang="hu-hu"),
                         "hetvenegy")
        self.assertEqual(pronounce_number(80, lang="hu-hu"), "nyolcvan")
        self.assertEqual(pronounce_number(74, lang="hu-hu"),
                         "hetvennégy")
        self.assertEqual(pronounce_number(79, lang="hu-hu"),
                         "hetvenkilenc")
        self.assertEqual(pronounce_number(91, lang="hu-hu"),
                         "kilencvenegy")
        self.assertEqual(pronounce_number(97, lang="hu-hu"),
                         "kilencvenhét")
        self.assertEqual(pronounce_number(300, lang="hu-hu"), "háromszáz")
        self.assertEqual(pronounce_number(1905, lang="hu-hu"),
                         "ezerkilencszázöt")
        self.assertEqual(pronounce_number(2001, lang="hu-hu"), "kétezer-egy")

    def test_convert_negative_int_hu(self):
        self.assertEqual(pronounce_number(-1, lang="hu-hu"), "mínusz egy")
        self.assertEqual(pronounce_number(-10, lang="hu-hu"), "mínusz tíz")
        self.assertEqual(pronounce_number(-15, lang="hu-hu"),
                         "mínusz tizenöt")
        self.assertEqual(pronounce_number(-20, lang="hu-hu"), "mínusz húsz")
        self.assertEqual(pronounce_number(-27, lang="hu-hu"),
                         "mínusz huszonhét")
        self.assertEqual(pronounce_number(-30, lang="hu-hu"), "mínusz harminc")
        self.assertEqual(pronounce_number(-33, lang="hu-hu"),
                         "mínusz harminchárom")

    def test_convert_decimals_hu(self):
        self.assertEqual(pronounce_number(1.234, lang="hu-hu"),
                         "egy egész huszonhárom század")
        self.assertEqual(pronounce_number(21.234, lang="hu-hu"),
                         "huszonegy egész huszonhárom század")
        self.assertEqual(pronounce_number(21.234, lang="hu-hu", places=1),
                         "huszonegy egész két tized")
        self.assertEqual(pronounce_number(21.234, lang="hu-hu", places=0),
                         "huszonegy")
        self.assertEqual(pronounce_number(21.234, lang="hu-hu", places=3),
                         "huszonegy egész kétszázharmincnégy ezred")
        self.assertEqual(pronounce_number(21.234, lang="hu-hu", places=4),
                         "huszonegy egész kétezer-háromszáznegyven tízezred")
        self.assertEqual(pronounce_number(21.234, lang="hu-hu", places=5),
                         "huszonegy egész huszonháromezer-négyszáz százezred")
        self.assertEqual(pronounce_number(-1.234, lang="hu-hu"),
                         "mínusz egy egész huszonhárom század")
        self.assertEqual(pronounce_number(-21.234, lang="hu-hu"),
                         "mínusz huszonegy egész huszonhárom század")
        self.assertEqual(pronounce_number(-21.234, lang="hu-hu", places=1),
                         "mínusz huszonegy egész két tized")
        self.assertEqual(pronounce_number(-21.234, lang="hu-hu", places=0),
                         "mínusz huszonegy")
        self.assertEqual(pronounce_number(-21.234, lang="hu-hu", places=3),
                         "mínusz huszonegy egész kétszázharmincnégy ezred")
        self.assertEqual(pronounce_number(-21.234, lang="hu-hu", places=4),
                         "mínusz huszonegy egész "
                         "kétezer-háromszáznegyven tízezred")
        self.assertEqual(pronounce_number(-21.234, lang="hu-hu", places=5),
                         "mínusz huszonegy egész "
                         "huszonháromezer-négyszáz százezred")


# def nice_time(dt, lang="hu-hu", speech=True, use_24hour=False,
#              use_ampm=False):
class TestNiceDateFormat_hu(unittest.TestCase):
    def test_convert_times_hu(self):
        dt = datetime.datetime(2017, 1, 31,
                               13, 22, 3)

        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "egy óra huszonkettő")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_ampm=True),
                         "délután egy óra huszonkettő")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False),
                         "1:22")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_ampm=True),
                         "1:22 PM")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=True),
                         "tizenhárom óra huszonkettő")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=False),
                         "tizenhárom óra huszonkettő")

        dt = datetime.datetime(2017, 1, 31,
                               13, 0, 3)
        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "egy óra")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_ampm=True),
                         "délután egy óra")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False),
                         "1:00")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_ampm=True),
                         "1:00 PM")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=True),
                         "tizenhárom óra")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=False),
                         "tizenhárom óra")

        dt = datetime.datetime(2017, 1, 31,
                               13, 2, 3)
        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "egy óra kettő")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_ampm=True),
                         "délután egy óra kettő")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False),
                         "1:02")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_ampm=True),
                         "1:02 PM")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=True),
                         "tizenhárom óra kettő")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=False),
                         "tizenhárom óra kettő")

        dt = datetime.datetime(2017, 1, 31,
                               0, 2, 3)
        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "tizenkét óra kettő")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_ampm=True),
                         "éjjel tizenkét óra kettő")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False),
                         "12:02")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_ampm=True),
                         "12:02 AM")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=True),
                         "nulla óra kettő")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=False),
                         "nulla óra kettő")

        dt = datetime.datetime(2017, 1, 31,
                               12, 15, 9)
        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "tizenkét óra tizenöt")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_ampm=True),
                         "délután tizenkét óra tizenöt")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_ampm=True),
                         "12:15 PM")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=True),
                         "tizenkét óra tizenöt")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=False),
                         "tizenkét óra tizenöt")

        dt = datetime.datetime(2017, 1, 31,
                               19, 40, 49)
        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "hét óra negyven")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_ampm=True),
                         "este hét óra negyven")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False),
                         "7:40")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_ampm=True),
                         "7:40 PM")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="hu-hu", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=True),
                         "tizenkilenc óra negyven")
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True,
                                   use_ampm=False),
                         "tizenkilenc óra negyven")

        dt = datetime.datetime(2017, 1, 31,
                               1, 15, 00)
        self.assertEqual(nice_time(dt, lang="hu-hu", use_24hour=True),
                         "egy óra tizenöt")

        dt = datetime.datetime(2017, 1, 31,
                               1, 35, 00)
        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "egy óra harmincöt")

        dt = datetime.datetime(2017, 1, 31,
                               1, 45, 00)
        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "egy óra negyvenöt")

        dt = datetime.datetime(2017, 1, 31,
                               4, 50, 00)
        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "négy óra ötven")

        dt = datetime.datetime(2017, 1, 31,
                               5, 55, 00)
        self.assertEqual(nice_time(dt, lang="hu-hu"),
                         "öt óra ötvenöt")

        dt = datetime.datetime(2017, 1, 31,
                               5, 30, 00)
        self.assertEqual(nice_time(dt, lang="hu-hu", use_ampm=True),
                         "reggel öt óra harminc")


if __name__ == "__main__":
    unittest.main()
