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
# from mycroft.util.lang.format_sv import nice_response_sv
from mycroft.util.lang.format_sv import pronounce_ordinal_sv

# fractions are not capitalized for now
NUMBERS_FIXTURE_sv = {
    1.435634: '1.436',
    2: '2',
    5.0: '5',
    1234567890: '1234567890',
    12345.67890: '12345.679',
    0.027: '0.027',
    0.5: 'en halv',
    1.333: '1 och en tredjedel',
    2.666: '2 och 2 tredjedelar',
    0.25: 'en fjärdedel',
    1.25: '1 och en fjärdedel',
    0.75: '3 fjärdedelar',
    1.75: '1 och 3 fjärdedelar',
    3.4: '3 och 2 femtedelar',
    16.8333: '16 och 5 sjättedelar',
    12.5714: '12 och 4 sjundedelar',
    9.625: '9 och 5 åttondelar',
    6.777: '6 och 7 niondelar',
    3.1: '3 och en tiondel',
    2.272: '2 och 3 elftedelar',
    5.583: '5 och 7 tolftedelar',
    8.384: '8 och 5 trettondelar',
    0.071: 'en fjortondel',
    6.466: '6 och 7 femtondelar',
    8.312: '8 och 5 sextondelar',
    2.176: '2 och 3 sjuttondelar',
    200.722: '200 och 13 artondelar',
    7.421: '7 och 8 nittondelar',
    0.05: 'en tjugondel'
}


# class TestNiceResponse(unittest.TestCase):
#    def test_replace_ordinal(self):
#        self.assertEqual(nice_response_sv("det er den 31. maj"),
#                                          "det er den enogtredifte maj")
#        self.assertEqual(nice_response_sv("Det begynder den 31. maj"),
#                                          "Det begynder den enogtrefte maj")
#        self.assertEqual(nice_response_sv("den 31. mai"),
#                                         "den enogtrefte maj")
#        self.assertEqual(nice_response_sv("10 ^ 2"), "ti to")


class TestNiceNumberFormat(unittest.TestCase):
    def test_convert_float_to_nice_number(self):
        for number, number_str in NUMBERS_FIXTURE_sv.items():
            self.assertEqual(nice_number(number, lang="sv-se"), number_str,
                             'should format {} as {} and not {}'.format(
                                 number, number_str,
                                 nice_number(number, lang="sv-se")))

    def test_specify_danominator(self):
        self.assertEqual(nice_number(5.5, lang="sv-se",
                                     denominators=[1, 2, 3]), '5 och en halv',
                         'should format 5.5 as 5 und ein halb not {}'.format(
                             nice_number(5.5, denominators=[1, 2, 3])))
        self.assertEqual(nice_number(2.333, lang="sv-se", denominators=[1, 2]),
                         '2.333',
                         'should format 2,333 as 2.333 not {}'.format(
                             nice_number(2.333, lang="sv-se",
                                         denominators=[1, 2])))

    def test_no_speech(self):
        self.assertEqual(nice_number(6.777, speech=False),
                         '6 7/9',
                         'should format 6.777 as 6 7/9 not {}'.format(
                             nice_number(6.777, lang="sv-se", speech=False)))
        self.assertEqual(nice_number(6.0, speech=False),
                         '6',
                         'should format 6.0 as 6 not {}'.format(
                             nice_number(6.0, lang="sv-se", speech=False)))


class TestPronounceOrdinal(unittest.TestCase):
    def test_convert_int_sv(self):
        self.assertEqual(pronounce_ordinal_sv(0),
                         "noll")
        self.assertEqual(pronounce_ordinal_sv(1),
                         "första")
        self.assertEqual(pronounce_ordinal_sv(3),
                         "tredje")
        self.assertEqual(pronounce_ordinal_sv(5),
                         "femte")
        self.assertEqual(pronounce_ordinal_sv(21),
                         "tjugoförsta")
        self.assertEqual(pronounce_ordinal_sv(2000),
                         "tvåtusende")
        self.assertEqual(pronounce_ordinal_sv(1000),
                         "ettusende")
#         self.assertEqual(pronounce_ordinal_sv(123456),
#                         "ethundredetreogtyvetusindefirehundredeseksog\
#                          halvtresende")


class TestPronounceNumber(unittest.TestCase):
    def test_convert_int_sv(self):
        self.assertEqual(pronounce_number(123456789123456789, lang="sv-se"),
                         "etthundratjugotrebiljarder "
                         "fyrahundrafemtiosexbiljoner "
                         "sjuhundraåttioniomiljarder "
                         "etthundratjugotremiljoner "
                         "fyrahundrafemtiosextusen "
                         "sjuhundraåttionio")
        self.assertEqual(pronounce_number(1, lang="sv-se"), "en")
        self.assertEqual(pronounce_number(10, lang="sv-se"), "tio")
        self.assertEqual(pronounce_number(15, lang="sv-se"), "femton")
        self.assertEqual(pronounce_number(20, lang="sv-se"), "tjugo")
        self.assertEqual(pronounce_number(27, lang="sv-se"), "tjugosju")
        self.assertEqual(pronounce_number(30, lang="sv-se"), "trettio")
        self.assertEqual(pronounce_number(33, lang="sv-se"), "trettiotre")
        self.assertEqual(pronounce_number(71, lang="sv-se"), "sjuttioen")
        self.assertEqual(pronounce_number(80, lang="sv-se"), "åttio")
        self.assertEqual(pronounce_number(74, lang="sv-se"), "sjuttiofyra")
        self.assertEqual(pronounce_number(79, lang="sv-se"), "sjuttionio")
        self.assertEqual(pronounce_number(91, lang="sv-se"), "nittioen")
        self.assertEqual(pronounce_number(97, lang="sv-se"), "nittiosju")
        self.assertEqual(pronounce_number(300, lang="sv-se"), "trehundra")
        self.assertEqual(pronounce_number(10000001, lang="sv-se"),
                         "tiomiljoner en")

    def test_convert_negative_int_sv(self):
        self.assertEqual(pronounce_number(-1, lang="sv-se"),
                         "minus en")
        self.assertEqual(pronounce_number(-10, lang="sv-se"),
                         "minus tio")
        self.assertEqual(pronounce_number(-15, lang="sv-se"),
                         "minus femton")
        self.assertEqual(pronounce_number(-20, lang="sv-se"),
                         "minus tjugo")
        self.assertEqual(pronounce_number(-27, lang="sv-se"),
                         "minus tjugosju")
        self.assertEqual(pronounce_number(-30, lang="sv-se"),
                         "minus trettio")
        self.assertEqual(pronounce_number(-33, lang="sv-se"),
                         "minus trettiotre")

    def test_convert_dacimals_sv(self):
        self.assertEqual(pronounce_number(1.1, lang="sv-se", places=1),
                         "en komma en")
        self.assertEqual(pronounce_number(1.234, lang="sv-se"),
                         "en komma två tre")
        self.assertEqual(pronounce_number(21.234, lang="sv-se"),
                         "tjugoen komma två tre")
        self.assertEqual(pronounce_number(21.234, lang="sv-se", places=1),
                         "tjugoen komma två")
        self.assertEqual(pronounce_number(21.234, lang="sv-se", places=0),
                         "tjugoen")
        self.assertEqual(pronounce_number(21.234, lang="sv-se", places=3),
                         "tjugoen komma två tre fyra")
        self.assertEqual(pronounce_number(21.234, lang="sv-se", places=4),
                         "tjugoen komma två tre fyra noll")
        self.assertEqual(pronounce_number(21.234, lang="sv-se", places=5),
                         "tjugoen komma två tre fyra noll noll")
        self.assertEqual(pronounce_number(-1.234, lang="sv-se"),
                         "minus en komma två tre")
        self.assertEqual(pronounce_number(-21.234, lang="sv-se"),
                         "minus tjugoen komma två tre")
        self.assertEqual(pronounce_number(-21.234, lang="sv-se", places=1),
                         "minus tjugoen komma två")
        self.assertEqual(pronounce_number(-21.234, lang="sv-se", places=0),
                         "minus tjugoen")
        self.assertEqual(pronounce_number(-21.234, lang="sv-se", places=3),
                         "minus tjugoen komma två tre fyra")
        self.assertEqual(pronounce_number(-21.234, lang="sv-se", places=4),
                         "minus tjugoen komma två tre fyra noll")
        self.assertEqual(pronounce_number(-21.234, lang="sv-se", places=5),
                         "minus tjugoen komma två tre fyra noll noll")


# def nice_time(dt, lang="sv-se", speech=True, use_24hour=False,
#              use_ampm=False):
class TestNiceDateFormat_sv(unittest.TestCase):
    def test_convert_times_sv(self):
        dt = datetime.datetime(2017, 1, 31, 13, 22, 3)

        self.assertEqual(nice_time(dt, lang="sv-se"),
                         "tjugotvå minuter över ett")
        self.assertEqual(nice_time(dt, lang="sv-se", use_ampm=True),
                         "tjugotvå minuter över ett på eftermiddagen")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False),
                         "01:22")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_ampm=True),
                         "01:22 PM")
        self.assertEqual(nice_time(dt, lang="sv-se",
                                   speech=False, use_24hour=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=True),
                         "tretton tjugotvå")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=False),
                         "tretton tjugotvå")

        dt = datetime.datetime(2017, 1, 31, 13, 0, 3)
        self.assertEqual(nice_time(dt, lang="sv-se"), "ett")
        self.assertEqual(nice_time(dt, lang="sv-se", use_ampm=True),
                         "ett på eftermiddagen")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False),
                         "01:00")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_ampm=True),
                         "01:00 PM")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=True),
                         "tretton")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=False),
                         "tretton")

        dt = datetime.datetime(2017, 1, 31, 13, 2, 3)
        self.assertEqual(nice_time(dt, lang="sv-se"), "två minuter över ett")
        self.assertEqual(nice_time(dt, lang="sv-se", use_ampm=True),
                         "två minuter över ett på eftermiddagen")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False),
                         "01:02")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_ampm=True),
                         "01:02 PM")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=True),
                         "tretton noll två")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=False),
                         "tretton noll två")

        dt = datetime.datetime(2017, 1, 31, 0, 2, 3)
        self.assertEqual(nice_time(dt, lang="sv-se"), "två minuter över tolv")
        self.assertEqual(nice_time(dt, lang="sv-se", use_ampm=True),
                         "två minuter över tolv på natten")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False),
                         "12:02")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_ampm=True),
                         "12:02 AM")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=True),
                         "noll noll två")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=False),
                         "noll noll två")

        dt = datetime.datetime(2017, 1, 31, 12, 15, 9)
        self.assertEqual(nice_time(dt, lang="sv-se"), "kvart över tolv")
        self.assertEqual(nice_time(dt, lang="sv-se", use_ampm=True),
                         "kvart över tolv på eftermiddagen")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_ampm=True),
                         "12:15 PM")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=True),
                         "tolv femton")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=False),
                         "tolv femton")

        dt = datetime.datetime(2017, 1, 31, 19, 40, 49)
        self.assertEqual(nice_time(dt, lang="sv-se"), "tjugo minuter i åtta")
        self.assertEqual(nice_time(dt, lang="sv-se", use_ampm=True),
                         "tjugo minuter i åtta på kvällen")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False),
                         "07:40")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_ampm=True),
                         "07:40 PM")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="sv-se", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=True),
                         "nitton fyrtio")
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True,
                                   use_ampm=False),
                         "nitton fyrtio")

        dt = datetime.datetime(2017, 1, 31, 1, 15, 00)
        self.assertEqual(nice_time(dt, lang="sv-se", use_24hour=True),
                         "ett femton")

        dt = datetime.datetime(2017, 1, 31, 1, 35, 00)
        self.assertEqual(nice_time(dt, lang="sv-se"),
                         "tjugofem minuter i två")

        dt = datetime.datetime(2017, 1, 31, 1, 45, 00)
        self.assertEqual(nice_time(dt, lang="sv-se"), "kvart i två")

        dt = datetime.datetime(2017, 1, 31, 4, 50, 00)
        self.assertEqual(nice_time(dt, lang="sv-se"), "tio i fem")

        dt = datetime.datetime(2017, 1, 31, 5, 55, 00)
        self.assertEqual(nice_time(dt, lang="sv-se"), "fem i sex")

        dt = datetime.datetime(2017, 1, 31, 5, 30, 00)
        self.assertEqual(nice_time(dt, lang="sv-se", use_ampm=True),
                         "halv sex på morgonen")


if __name__ == "__main__":
    unittest.main()
