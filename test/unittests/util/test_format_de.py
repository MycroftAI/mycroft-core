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
import datetime

from mycroft.util.lang import get_active_lang, set_active_lang
from mycroft.util.format import nice_number
from mycroft.util.format import nice_time
from mycroft.util.format import pronounce_number
from mycroft.util.lang.format_de import nice_response_de
from mycroft.util.lang.format_de import pronounce_ordinal_de
from mycroft.util.format import join_list


# fractions are not capitalized for now
NUMBERS_FIXTURE_DE = {
    1.435634: '1,436',
    2: '2',
    5.0: '5',
    1234567890: '1234567890',
    12345.67890: u'12345,679',
    0.027: '0,027',
    0.5: 'ein halb',
    1.333: '1 und ein drittel',
    2.666: '2 und 2 drittel',
    0.25: 'ein viertel',
    1.25: '1 und ein viertel',
    0.75: '3 viertel',
    1.75: '1 und 3 viertel',
    3.4: u'3 und 2 fünftel',
    16.8333: u'16 und 5 sechstel',
    12.5714: u'12 und 4 siebtel',
    9.625: u'9 und 5 achtel',
    6.777: '6 und 7 neuntel',
    3.1: '3 und ein zehntel',
    2.272: '2 und 3 elftel',
    5.583: u'5 und 7 zwölftel',
    8.384: '8 und 5 dreizehntel',
    0.071: 'ein vierzehntel',
    6.466: u'6 und 7 fünfzehntel',
    8.312: '8 und 5 sechzehntel',
    2.176: '2 und 3 siebzehntel',
    200.722: '200 und 13 achtzehntel',
    7.421: '7 und 8 neunzehntel',
    0.05: 'ein zwanzigstel'
}


class TestNiceResponse(unittest.TestCase):
    def test_replace_ordinal(self):
        self.assertEqual(nice_response_de("dies ist der 31. mai"),
                         "dies ist der einunddreißigste mai")
        self.assertEqual(nice_response_de("es fängt am 31. mai an"),
                         "es fängt am einunddreißigsten mai an")
        self.assertEqual(nice_response_de("der 31. mai"),
                         "der einunddreißigste mai")
        self.assertEqual(nice_response_de("10 ^ 2"),
                         "10 hoch 2")


class TestNiceNumberFormat(unittest.TestCase):
    def setUp(self):
        self.old_lang = get_active_lang()
        set_active_lang("de-de")

    def tearDown(self):
        set_active_lang(self.old_lang)

    def test_convert_float_to_nice_number(self):
        for number, number_str in NUMBERS_FIXTURE_DE.items():
            self.assertEqual(nice_number(number), number_str,
                             'should format {} as {} and not {}'.format(
                                 number, number_str,
                                 nice_number(number)))

    def test_specify_denominator(self):
        self.assertEqual(nice_number(5.5,
                                     denominators=[1, 2, 3]), '5 und ein halb',
                         'should format 5.5 as 5 und ein halb not {}'.format(
                             nice_number(5.5, denominators=[1, 2, 3])))
        self.assertEqual(nice_number(2.333, denominators=[1, 2]),
                         '2,333',
                         'should format 2,333 as 2,333 not {}'.format(
                             nice_number(2.333,
                                         denominators=[1, 2])))

    def test_no_speech(self):
        self.assertEqual(nice_number(6.777, speech=False),
                         '6 7/9',
                         'should format 6.777 as 6 7/9 not {}'.format(
                             nice_number(6.777, speech=False)))
        self.assertEqual(nice_number(6.0, speech=False),
                         '6',
                         'should format 6.0 as 6 not {}'.format(
                             nice_number(6.0, speech=False)))


class TestPronounceOrdinal(unittest.TestCase):
    def test_convert_int_de(self):
        self.assertEqual(pronounce_ordinal_de(0),
                         "nullte")
        self.assertEqual(pronounce_ordinal_de(1),
                         "erste")
        self.assertEqual(pronounce_ordinal_de(3),
                         "dritte")
        self.assertEqual(pronounce_ordinal_de(5),
                         u"fünfte")
        self.assertEqual(pronounce_ordinal_de(1000),
                         "eintausendste")
        self.assertEqual(pronounce_ordinal_de(123456),
                         "einhundertdreiundzwanzigtausendvierhundertsechsundf"
                         "ünfzigste")


# def pronounce_number(number, lang="de-de", places=2):
class TestPronounceNumber(unittest.TestCase):
    def setUp(self):
        self.old_lang = get_active_lang()
        set_active_lang("de-de")

    def tearDown(self):
        set_active_lang(self.old_lang)

    def test_convert_int_de(self):
        self.assertEqual(pronounce_number(123456789123456789),
                         "einhundertdreiundzwanzig Billiarden "
                         "vierhundertsechsundfünfzig Billionen "
                         "siebenhundertneunundachtzig Milliarden "
                         "einhundertdreiundzwanzig Millionen "
                         "vierhundertsechsundfünfzigtausendsiebenhundert"
                         "neunundachtzig")
        self.assertEqual(pronounce_number(1), "eins")
        self.assertEqual(pronounce_number(10), "zehn")
        self.assertEqual(pronounce_number(15), u"fünfzehn")
        self.assertEqual(pronounce_number(20), "zwanzig")
        self.assertEqual(pronounce_number(27), "siebenundzwanzig")
        self.assertEqual(pronounce_number(30), u"dreißig")
        self.assertEqual(pronounce_number(33), u"dreiunddreißig")

        self.assertEqual(pronounce_number(71), "einundsiebzig")
        self.assertEqual(pronounce_number(80), "achtzig")
        self.assertEqual(pronounce_number(74), "vierundsiebzig")
        self.assertEqual(pronounce_number(79), "neunundsiebzig")
        self.assertEqual(pronounce_number(91), "einundneunzig")
        self.assertEqual(pronounce_number(97), "siebenundneunzig")
        self.assertEqual(pronounce_number(300), "dreihundert")

    def test_convert_negative_int_de(self):
        self.assertEqual(pronounce_number(-1), "minus eins")
        self.assertEqual(pronounce_number(-10), "minus zehn")
        self.assertEqual(pronounce_number(-15), u"minus fünfzehn")
        self.assertEqual(pronounce_number(-20), "minus zwanzig")
        self.assertEqual(pronounce_number(-27), "minus siebenundzwanzig")
        self.assertEqual(pronounce_number(-30), u"minus dreißig")
        self.assertEqual(pronounce_number(-33), u"minus dreiunddreißig")

    def test_convert_decimals_de(self):
        self.assertEqual(pronounce_number(1.234),
                         "eins Komma zwei drei")
        self.assertEqual(pronounce_number(21.234),
                         "einundzwanzig Komma zwei drei")
        self.assertEqual(pronounce_number(21.234, places=1),
                         "einundzwanzig Komma zwei")
        self.assertEqual(pronounce_number(21.234, places=0),
                         "einundzwanzig")
        self.assertEqual(pronounce_number(21.234, places=3),
                         "einundzwanzig Komma zwei drei vier")
        self.assertEqual(pronounce_number(21.234, places=4),
                         "einundzwanzig Komma zwei drei vier null")
        self.assertEqual(pronounce_number(21.234, places=5),
                         "einundzwanzig Komma zwei drei vier null null")
        self.assertEqual(pronounce_number(-1.234),
                         "minus eins Komma zwei drei")
        self.assertEqual(pronounce_number(-21.234),
                         "minus einundzwanzig Komma zwei drei")
        self.assertEqual(pronounce_number(-21.234, places=1),
                         "minus einundzwanzig Komma zwei")
        self.assertEqual(pronounce_number(-21.234, places=0),
                         "minus einundzwanzig")
        self.assertEqual(pronounce_number(-21.234, places=3),
                         "minus einundzwanzig Komma zwei drei vier")
        self.assertEqual(pronounce_number(-21.234, places=4),
                         "minus einundzwanzig Komma zwei drei vier null")
        self.assertEqual(pronounce_number(-21.234, places=5),
                         "minus einundzwanzig Komma zwei drei vier null null")


# def nice_time(dt, lang="de-de", speech=True, use_24hour=False,
#              use_ampm=False):
class TestNiceDateFormat_de(unittest.TestCase):
    def setUp(self):
        self.old_lang = get_active_lang()
        set_active_lang("de-de")

    def tearDown(self):
        set_active_lang(self.old_lang)

    def test_convert_times_de(self):
        dt = datetime.datetime(2017, 1, 31,
                               13, 22, 3)

        self.assertEqual(nice_time(dt),
                         "ein Uhr zweiundzwanzig")
        self.assertEqual(nice_time(dt, use_ampm=True),
                         "ein Uhr zweiundzwanzig nachmittags")
        self.assertEqual(nice_time(dt, speech=False),
                         "1:22")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_ampm=True),
                         "1:22 PM")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True),
                         "13:22")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:22")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=True),
                         "dreizehn Uhr zweiundzwanzig")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=False),
                         "dreizehn Uhr zweiundzwanzig")

        dt = datetime.datetime(2017, 1, 31,
                               13, 0, 3)
        self.assertEqual(nice_time(dt),
                         "ein Uhr")
        self.assertEqual(nice_time(dt, use_ampm=True),
                         "ein Uhr nachmittags")
        self.assertEqual(nice_time(dt, speech=False),
                         "1:00")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_ampm=True),
                         "1:00 PM")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True),
                         "13:00")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:00")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=True),
                         "dreizehn Uhr")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=False),
                         "dreizehn Uhr")

        dt = datetime.datetime(2017, 1, 31,
                               13, 2, 3)
        self.assertEqual(nice_time(dt),
                         "ein Uhr zwei")
        self.assertEqual(nice_time(dt, use_ampm=True),
                         "ein Uhr zwei nachmittags")
        self.assertEqual(nice_time(dt, speech=False),
                         "1:02")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_ampm=True),
                         "1:02 PM")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True),
                         "13:02")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:02")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=True),
                         "dreizehn Uhr zwei")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=False),
                         "dreizehn Uhr zwei")

        dt = datetime.datetime(2017, 1, 31,
                               0, 2, 3)
        self.assertEqual(nice_time(dt),
                         u"zwölf Uhr zwei")
        self.assertEqual(nice_time(dt, use_ampm=True),
                         u"zwölf Uhr zwei nachts")
        self.assertEqual(nice_time(dt, speech=False),
                         "12:02")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_ampm=True),
                         "12:02 AM")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True),
                         "00:02")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True, use_ampm=True),
                         "00:02")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=True),
                         "null Uhr zwei")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=False),
                         "null Uhr zwei")

        dt = datetime.datetime(2017, 1, 31,
                               12, 15, 9)
        self.assertEqual(nice_time(dt),
                         u"zwölf Uhr fünfzehn")
        self.assertEqual(nice_time(dt, use_ampm=True),
                         u"zwölf Uhr fünfzehn nachmittags")
        self.assertEqual(nice_time(dt, speech=False),
                         "12:15")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_ampm=True),
                         "12:15 PM")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True),
                         "12:15")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True, use_ampm=True),
                         "12:15")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=True),
                         u"zwölf Uhr fünfzehn")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=False),
                         u"zwölf Uhr fünfzehn")

        dt = datetime.datetime(2017, 1, 31,
                               19, 40, 49)
        self.assertEqual(nice_time(dt),
                         "sieben Uhr vierzig")
        self.assertEqual(nice_time(dt, use_ampm=True),
                         "sieben Uhr vierzig abends")
        self.assertEqual(nice_time(dt, speech=False),
                         "7:40")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_ampm=True),
                         "7:40 PM")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True),
                         "19:40")
        self.assertEqual(nice_time(dt, speech=False,
                                   use_24hour=True, use_ampm=True),
                         "19:40")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=True),
                         "neunzehn Uhr vierzig")
        self.assertEqual(nice_time(dt, use_24hour=True,
                                   use_ampm=False),
                         "neunzehn Uhr vierzig")

        dt = datetime.datetime(2017, 1, 31,
                               1, 15, 00)
        self.assertEqual(nice_time(dt, use_24hour=True),
                         u"ein Uhr fünfzehn")

        dt = datetime.datetime(2017, 1, 31,
                               1, 35, 00)
        self.assertEqual(nice_time(dt),
                         u"ein Uhr fünfunddreißig")

        dt = datetime.datetime(2017, 1, 31,
                               1, 45, 00)
        self.assertEqual(nice_time(dt),
                         u"ein Uhr fünfundvierzig")

        dt = datetime.datetime(2017, 1, 31,
                               4, 50, 00)
        self.assertEqual(nice_time(dt),
                         u"vier Uhr fünfzig")

        dt = datetime.datetime(2017, 1, 31,
                               5, 55, 00)
        self.assertEqual(nice_time(dt),
                         u"fünf Uhr fünfundfünfzig")

        dt = datetime.datetime(2017, 1, 31,
                               5, 30, 00)
        self.assertEqual(nice_time(dt, use_ampm=True),
                         u"fünf Uhr dreißig morgens")


class TestJoinList_de(unittest.TestCase):
    def setUp(self):
        self.old_lang = get_active_lang()
        set_active_lang("de-de")

    def tearDown(self):
        set_active_lang(self.old_lang)

    def test_join_list_de(self):
        self.assertEqual(join_list(['Hallo', 'Auf wieder Sehen'], 'and'),
                         'Hallo und Auf wieder Sehen')

        self.assertEqual(join_list(['A', 'B', 'C'], 'or'),
                         'A, B oder C')


if __name__ == "__main__":
    unittest.main()
