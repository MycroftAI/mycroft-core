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
from mycroft.util.lang.format_nl import nice_response_nl
from mycroft.util.lang.format_nl import pronounce_ordinal_nl

# fractions are not capitalized for now
NUMBERS_FIXTURE_NL = {
    1.435634: '1,436',
    2: '2',
    5.0: '5',
    1234567890: '1234567890',
    12345.67890: u'12345,679',
    0.027: '0,027',
    0.5: u'één half',
    1.333: '1 en één derde',
    2.666: '2 en 2 derde',
    0.25: u'één vierde',
    1.25: '1 en één vierde',
    0.75: '3 vierde',
    1.75: '1 en 3 vierde',
    3.4: '3 en 2 vijfde',
    16.8333: '16 en 5 zesde',
    12.5714: '12 en 4 zevende',
    9.625: '9 en 5 achtste',
    6.777: '6 en 7 negende',
    3.1: '3 en één tiende',
    2.272: '2 en 3 elfde',
    5.583: '5 en 7 twaalfde',
    8.384: '8 en 5 dertiende',
    0.071: u'één veertiende',
    6.466: '6 en 7 vijftiende',
    8.312: '8 en 5 zestiende',
    2.176: '2 en 3 zeventiende',
    200.722: '200 en 13 achttiende',
    7.421: '7 en 8 negentiende',
    0.05: u'één twintigste'
}


class TestNiceResponse(unittest.TestCase):
    def test_replace_ordinal(self):
        self.assertEqual(nice_response_nl("dit is 31 mei"),
                         "dit is éénendertig mei")
        self.assertEqual(nice_response_nl("het begint op 31 mei"),
                         "het begint op éénendertig mei")
        self.assertEqual(nice_response_nl("31 mei"),
                         "éénendertig mei")
        self.assertEqual(nice_response_nl("10 ^ 2"),
                         "10 tot de macht 2")


class TestNiceNumberFormat(unittest.TestCase):
    def test_convert_float_to_nice_number(self):
        for number, number_str in NUMBERS_FIXTURE_NL.items():
            self.assertEqual(nice_number(number, lang="nl-nl"), number_str,
                             'should format {} as {} and not {}'.format(
                                 number, number_str,
                                 nice_number(number, lang="nl-nl")))

    def test_specify_denominator(self):
        self.assertEqual(nice_number(5.5, lang="nl-nl",
                                     denominators=[1, 2, 3]), '5 en één half',
                         'should format 5.5 as 5 en één half not {}'.format(
                             nice_number(5.5, denominators=[1, 2, 3])))
        self.assertEqual(nice_number(2.333, lang="nl-nl", denominators=[1, 2]),
                         '2,333',
                         'should format 2,333 as 2,333 not {}'.format(
                             nice_number(2.333, lang="nl-nl",
                                         denominators=[1, 2])))

    def test_no_speech(self):
        self.assertEqual(nice_number(6.777, speech=False),
                         '6 7/9',
                         'should format 6.777 as 6 7/9 not {}'.format(
                             nice_number(6.777, lang="nl-nl", speech=False)))
        self.assertEqual(nice_number(6.0, speech=False),
                         '6',
                         'should format 6.0 as 6 not {}'.format(
                             nice_number(6.0, lang="nl-nl", speech=False)))


class TestPronounceOrdinal(unittest.TestCase):
    def test_convert_int_nl(self):
        self.assertEqual(pronounce_ordinal_nl(0), "nulste")
        self.assertEqual(pronounce_ordinal_nl(1), "eerste")
        self.assertEqual(pronounce_ordinal_nl(3), "derde")
        self.assertEqual(pronounce_ordinal_nl(5), "vijfde")
        self.assertEqual(pronounce_ordinal_nl(1000), u"éénduizendste")
        self.assertEqual(
            pronounce_ordinal_nl(123456),
            "éénhonderddrieentwintigduizendvierhonderdzesenvijftigste"
        )


# def pronounce_number(number, lang="nl-nl", places=2):
class TestPronounceNumber(unittest.TestCase):
    def test_convert_int_nl(self):
        self.assertEqual(pronounce_number(123456789123456789, lang="nl-nl"),
                         u"éénhonderddrieentwintig biljard "
                         "vierhonderdzesenvijftig biljoen "
                         "zevenhonderdnegenentachtig miljard "
                         "éénhonderddrieentwintig miljoen "
                         "vierhonderdzesenvijftigduizend"
                         "zevenhonderdnegenentachtig")
        self.assertEqual(pronounce_number(1, lang="nl-nl"), u"één")
        self.assertEqual(pronounce_number(10, lang="nl-nl"), "tien")
        self.assertEqual(pronounce_number(15, lang="nl-nl"), "vijftien")
        self.assertEqual(pronounce_number(20, lang="nl-nl"), "twintig")
        self.assertEqual(pronounce_number(27, lang="nl-nl"),
                         "zevenentwintig")
        self.assertEqual(pronounce_number(30, lang="nl-nl"), "dertig")
        self.assertEqual(pronounce_number(33, lang="nl-nl"), u"drieendertig")
        self.assertEqual(pronounce_number(71, lang="nl-nl"),
                         u"éénenzeventig")
        self.assertEqual(pronounce_number(80, lang="nl-nl"), "tachtig")
        self.assertEqual(pronounce_number(74, lang="nl-nl"),
                         "vierenzeventig")
        self.assertEqual(pronounce_number(79, lang="nl-nl"),
                         "negenenzeventig")
        self.assertEqual(pronounce_number(91, lang="nl-nl"),
                         u"éénennegentig")
        self.assertEqual(pronounce_number(97, lang="nl-nl"),
                         "zevenennegentig")
        self.assertEqual(pronounce_number(300, lang="nl-nl"), "driehonderd")

    def test_convert_negative_int_nl(self):
        self.assertEqual(pronounce_number(-1, lang="nl-nl"), u"min één")
        self.assertEqual(pronounce_number(-10, lang="nl-nl"), "min tien")
        self.assertEqual(pronounce_number(-15, lang="nl-nl"), "min vijftien")
        self.assertEqual(pronounce_number(-20, lang="nl-nl"), "min twintig")
        self.assertEqual(pronounce_number(-27, lang="nl-nl"),
                         "min zevenentwintig")
        self.assertEqual(pronounce_number(-30, lang="nl-nl"), u"min dertig")
        self.assertEqual(pronounce_number(-33, lang="nl-nl"),
                         u"min drieendertig")

    def test_convert_decimals_nl(self):
        self.assertEqual(pronounce_number(1.234, lang="nl-nl"),
                         u"één komma twee drie")
        self.assertEqual(pronounce_number(21.234, lang="nl-nl"),
                         u"éénentwintig komma twee drie")
        self.assertEqual(pronounce_number(21.234, lang="nl-nl", places=1),
                         u"éénentwintig komma twee")
        self.assertEqual(pronounce_number(21.234, lang="nl-nl", places=0),
                         u"éénentwintig")
        self.assertEqual(pronounce_number(21.234, lang="nl-nl", places=3),
                         u"éénentwintig komma twee drie vier")
        self.assertEqual(pronounce_number(21.234, lang="nl-nl", places=4),
                         u"éénentwintig komma twee drie vier nul")
        self.assertEqual(pronounce_number(21.234, lang="nl-nl", places=5),
                         u"éénentwintig komma twee drie vier nul nul")
        self.assertEqual(pronounce_number(-1.234, lang="nl-nl"),
                         u"min één komma twee drie")
        self.assertEqual(pronounce_number(-21.234, lang="nl-nl"),
                         u"min éénentwintig komma twee drie")
        self.assertEqual(pronounce_number(-21.234, lang="nl-nl", places=1),
                         u"min éénentwintig komma twee")
        self.assertEqual(pronounce_number(-21.234, lang="nl-nl", places=0),
                         u"min éénentwintig")
        self.assertEqual(pronounce_number(-21.234, lang="nl-nl", places=3),
                         u"min éénentwintig komma twee drie vier")
        self.assertEqual(pronounce_number(-21.234, lang="nl-nl", places=4),
                         u"min éénentwintig komma twee drie vier nul")
        self.assertEqual(pronounce_number(-21.234, lang="nl-nl", places=5),
                         u"min éénentwintig komma twee drie vier nul nul")


# def nice_time(dt, lang="nl-nl", speech=True, use_24hour=False,
#              use_ampm=False):
class TestNiceDateFormat_nl(unittest.TestCase):
    def test_convert_times_nl(self):
        dt = datetime.datetime(2017, 1, 31,
                               13, 22, 3)

        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         u"tweeentwintig over één")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_ampm=True),
                         u"tweeentwintig over één 's middags")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False),
                         "1:22")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_ampm=True),
                         "1:22 PM")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=True),
                         "dertien uur tweeentwintig")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=False),
                         "dertien uur tweeentwintig")

        dt = datetime.datetime(2017, 1, 31,
                               13, 0, 3)
        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         u"één uur")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_ampm=True),
                         u"één uur 's middags")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False),
                         "1:00")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_ampm=True),
                         "1:00 PM")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=True),
                         "dertien uur")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=False),
                         "dertien uur")

        dt = datetime.datetime(2017, 1, 31,
                               13, 2, 3)
        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         u"twee over één")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_ampm=True),
                         u"twee over één 's middags")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False),
                         "1:02")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_ampm=True),
                         "1:02 PM")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=True),
                         "dertien uur twee")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=False),
                         "dertien uur twee")

        dt = datetime.datetime(2017, 1, 31,
                               0, 2, 3)
        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         "twee over twaalf")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_ampm=True),
                         "twee over twaalf 's nachts")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False),
                         "12:02")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_ampm=True),
                         "12:02 AM")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=True),
                         "nul uur twee")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=False),
                         "nul uur twee")

        dt = datetime.datetime(2017, 1, 31,
                               12, 15, 9)
        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         "kwart over twaalf")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_ampm=True),
                         "kwart over twaalf 's middags")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_ampm=True),
                         "12:15 PM")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=True),
                         "twaalf uur vijftien")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=False),
                         "twaalf uur vijftien")

        dt = datetime.datetime(2017, 1, 31,
                               19, 40, 49)
        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         "twintig voor acht")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_ampm=True),
                         "twintig voor acht 's avonds")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False),
                         "7:40")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_ampm=True),
                         "7:40 PM")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="nl-nl", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=True),
                         "negentien uur veertig")
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True,
                                   use_ampm=False),
                         "negentien uur veertig")

        dt = datetime.datetime(2017, 1, 31,
                               1, 15, 00)
        self.assertEqual(nice_time(dt, lang="nl-nl", use_24hour=True),
                         u"één uur vijftien")

        dt = datetime.datetime(2017, 1, 31,
                               1, 35, 00)
        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         u"vijfentwintig voor twee")

        dt = datetime.datetime(2017, 1, 31,
                               1, 45, 00)
        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         u"kwart voor twee")

        dt = datetime.datetime(2017, 1, 31,
                               4, 50, 00)
        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         u"tien voor vijf")

        dt = datetime.datetime(2017, 1, 31,
                               5, 55, 00)
        self.assertEqual(nice_time(dt, lang="nl-nl"),
                         "vijf voor zes")

        dt = datetime.datetime(2017, 1, 31,
                               5, 30, 00)
        self.assertEqual(nice_time(dt, lang="nl-nl", use_ampm=True),
                         u"half zes 's nachts")


if __name__ == "__main__":
    unittest.main()
