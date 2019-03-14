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
# from mycroft.util.lang.format_da import nice_response_da
from mycroft.util.lang.format_da import pronounce_ordinal_da

# fractions are not capitalized for now
NUMBERS_FIXTURE_da = {
    1.435634: '1,436',
    2: '2',
    5.0: '5',
    1234567890: '1234567890',
    12345.67890: '12345,679',
    0.027: '0,027',
    0.5: '1 halv',
    1.333: '1 og 1 trediedel',
    2.666: '2 og 2 trediedele',
    0.25: '1 fjerdedel',
    1.25: '1 og 1 fjerdedel',
    0.75: '3 fjerdedele',
    1.75: '1 og 3 fjerdedele',
    3.4: '3 og 2 femtedele',
    16.8333: '16 og 5 sjettedele',
    12.5714: '12 og 4 syvendedele',
    9.625: '9 og 5 ottendedele',
    6.777: '6 og 7 niendedele',
    3.1: '3 og 1 tiendedel',
    2.272: '2 og 3 elftedele',
    5.583: '5 og 7 tolvtedele',
    8.384: '8 og 5 trettendedele',
    0.071: '1 fjortendedel',
    6.466: '6 og 7 femtendedele',
    8.312: '8 og 5 sejstendedele',
    2.176: '2 og 3 syttendedele',
    200.722: '200 og 13 attendedele',
    7.421: '7 og 8 nittendedele',
    0.05: '1 tyvendedel'
}


# class TestNiceResponse(unittest.TestCase):
#    def test_replace_ordinal(self):
#        self.assertEqual(nice_response_da("det er den 31. maj"),
#                                          "det er den enogtredifte maj")
#        self.assertEqual(nice_response_da("Det begynder den 31. maj"),
#                                          "Det begynder den enogtrefte maj")
#        self.assertEqual(nice_response_da("den 31. mai"),
#                                         "den enogtrefte maj")
#        self.assertEqual(nice_response_da("10 ^ 2"), "ti to")


class TestNiceNumberFormat(unittest.TestCase):
    def test_convert_float_to_nice_number(self):
        for number, number_str in NUMBERS_FIXTURE_da.items():
            self.assertEqual(nice_number(number, lang="da-dk"), number_str,
                             'should format {} as {} and not {}'.format(
                                 number, number_str,
                                 nice_number(number, lang="da-dk")))

    def test_specify_danominator(self):
        self.assertEqual(nice_number(5.5, lang="da-dk",
                                     denominators=[1, 2, 3]), '5 og 1 halv',
                         'should format 5.5 as 5 und ein halb not {}'.format(
                             nice_number(5.5, denominators=[1, 2, 3])))
        self.assertEqual(nice_number(2.333, lang="da-dk", denominators=[1, 2]),
                         '2,333',
                         'should format 2,333 as 2,333 not {}'.format(
                             nice_number(2.333, lang="da-dk",
                                         denominators=[1, 2])))

    def test_no_speech(self):
        self.assertEqual(nice_number(6.777, speech=False),
                         '6 7/9',
                         'should format 6.777 as 6 7/9 not {}'.format(
                             nice_number(6.777, lang="da-dk", speech=False)))
        self.assertEqual(nice_number(6.0, speech=False),
                         '6',
                         'should format 6.0 as 6 not {}'.format(
                             nice_number(6.0, lang="da-dk", speech=False)))


class TestPronounceOrdinal(unittest.TestCase):
    def test_convert_int_da(self):
        self.assertEqual(pronounce_ordinal_da(0),
                         "nulte")
        self.assertEqual(pronounce_ordinal_da(1),
                         "første")
        self.assertEqual(pronounce_ordinal_da(3),
                         "tredie")
        self.assertEqual(pronounce_ordinal_da(5),
                         "femte")
        self.assertEqual(pronounce_ordinal_da(21),
                         "enogtyvende")
        self.assertEqual(pronounce_ordinal_da(2000),
                         "totusindende")
        self.assertEqual(pronounce_ordinal_da(1000),
                         "ettusindende")
#         self.assertEqual(pronounce_ordinal_da(123456),
#                         "ethundredetreogtyvetusindefirehundredeseksog\
#                          halvtresende")


class TestPronounceNumber(unittest.TestCase):
    def test_convert_int_da(self):
        # self.assertEqual(pronounce_number(123456789123456789, lang="da-dk"),
        #                 "ethundredetreogtyvebilliarder"
        #                 "firehundredeseksoghalvtresbillioner"
        #                 "syvhundredeogfirsmiliarder"
        #                 "ethundredetreogtyvemillioner"
        #                 "firehundredeseksoghalvtrestusindesyvhundredeniog \
        #                  firs")
        self.assertEqual(pronounce_number(1, lang="da-dk"), "en")
        self.assertEqual(pronounce_number(10, lang="da-dk"), "ti")
        self.assertEqual(pronounce_number(15, lang="da-dk"), "femten")
        self.assertEqual(pronounce_number(20, lang="da-dk"), "tyve")
        self.assertEqual(pronounce_number(27, lang="da-dk"), "syvogtyve")
        self.assertEqual(pronounce_number(30, lang="da-dk"), "tredive")
        self.assertEqual(pronounce_number(33, lang="da-dk"), "treogtredive")
        self.assertEqual(pronounce_number(71, lang="da-dk"), "enoghalvfjers")
        self.assertEqual(pronounce_number(80, lang="da-dk"), "firs")
        self.assertEqual(pronounce_number(74, lang="da-dk"), "fireoghalvfjers")
        self.assertEqual(pronounce_number(79, lang="da-dk"), "nioghalvfjers")
        self.assertEqual(pronounce_number(91, lang="da-dk"), "enoghalvfems")
        self.assertEqual(pronounce_number(97, lang="da-dk"), "syvoghalvfems")
        self.assertEqual(pronounce_number(300, lang="da-dk"), "trehundrede")

    def test_convert_negative_int_da(self):
        self.assertEqual(pronounce_number(-1, lang="da-dk"),
                         "minus en")
        self.assertEqual(pronounce_number(-10, lang="da-dk"),
                         "minus ti")
        self.assertEqual(pronounce_number(-15, lang="da-dk"),
                         "minus femten")
        self.assertEqual(pronounce_number(-20, lang="da-dk"),
                         "minus tyve")
        self.assertEqual(pronounce_number(-27, lang="da-dk"),
                         "minus syvogtyve")
        self.assertEqual(pronounce_number(-30, lang="da-dk"),
                         "minus tredive")
        self.assertEqual(pronounce_number(-33, lang="da-dk"),
                         "minus treogtredive")

    def test_convert_dacimals_da(self):
        self.assertEqual(pronounce_number(1.234, lang="da-dk"),
                         "en komma to tre")
        self.assertEqual(pronounce_number(21.234, lang="da-dk"),
                         "enogtyve komma to tre")
        self.assertEqual(pronounce_number(21.234, lang="da-dk", places=1),
                         "enogtyve komma to")
        self.assertEqual(pronounce_number(21.234, lang="da-dk", places=0),
                         "enogtyve")
        self.assertEqual(pronounce_number(21.234, lang="da-dk", places=3),
                         "enogtyve komma to tre fire")
        self.assertEqual(pronounce_number(21.234, lang="da-dk", places=4),
                         "enogtyve komma to tre fire nul")
        self.assertEqual(pronounce_number(21.234, lang="da-dk", places=5),
                         "enogtyve komma to tre fire nul nul")
        self.assertEqual(pronounce_number(-1.234, lang="da-dk"),
                         "minus en komma to tre")
        self.assertEqual(pronounce_number(-21.234, lang="da-dk"),
                         "minus enogtyve komma to tre")
        self.assertEqual(pronounce_number(-21.234, lang="da-dk", places=1),
                         "minus enogtyve komma to")
        self.assertEqual(pronounce_number(-21.234, lang="da-dk", places=0),
                         "minus enogtyve")
        self.assertEqual(pronounce_number(-21.234, lang="da-dk", places=3),
                         "minus enogtyve komma to tre fire")
        self.assertEqual(pronounce_number(-21.234, lang="da-dk", places=4),
                         "minus enogtyve komma to tre fire nul")
        self.assertEqual(pronounce_number(-21.234, lang="da-dk", places=5),
                         "minus enogtyve komma to tre fire nul nul")


# def nice_time(dt, lang="da-dk", speech=True, use_24hour=False,
#              use_ampm=False):
class TestNiceDateFormat_da(unittest.TestCase):
    def test_convert_times_da(self):
        dt = datetime.datetime(2017, 1, 31, 13, 22, 3)

        self.assertEqual(nice_time(dt, lang="da-dk"),
                         "et toogtyve")
        self.assertEqual(nice_time(dt, lang="da-dk", use_ampm=True),
                         "et toogtyve om eftermiddagen")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False),
                         "01:22")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_ampm=True),
                         "01:22 PM")
        self.assertEqual(nice_time(dt, lang="da-dk",
                                   speech=False, use_24hour=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=True),
                         "tretten toogtyve")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=False),
                         "tretten toogtyve")

        dt = datetime.datetime(2017, 1, 31, 13, 0, 3)
        self.assertEqual(nice_time(dt, lang="da-dk"), "et")
        self.assertEqual(nice_time(dt, lang="da-dk", use_ampm=True),
                         "et om eftermiddagen")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False),
                         "01:00")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_ampm=True),
                         "01:00 PM")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=True),
                         "tretten")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=False),
                         "tretten")

        dt = datetime.datetime(2017, 1, 31, 13, 2, 3)
        self.assertEqual(nice_time(dt, lang="da-dk"), "et nul to")
        self.assertEqual(nice_time(dt, lang="da-dk", use_ampm=True),
                         "et nul to om eftermiddagen")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False),
                         "01:02")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_ampm=True),
                         "01:02 PM")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=True),
                         "tretten nul to")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=False),
                         "tretten nul to")

        dt = datetime.datetime(2017, 1, 31, 0, 2, 3)
        self.assertEqual(nice_time(dt, lang="da-dk"), "tolv nul to")
        self.assertEqual(nice_time(dt, lang="da-dk", use_ampm=True),
                         "tolv nul to om natten")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False),
                         "12:02")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_ampm=True),
                         "12:02 AM")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=True),
                         "nul nul to")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=False),
                         "nul nul to")

        dt = datetime.datetime(2017, 1, 31, 12, 15, 9)
        self.assertEqual(nice_time(dt, lang="da-dk"), "tolv femten")
        self.assertEqual(nice_time(dt, lang="da-dk", use_ampm=True),
                         "tolv femten om eftermiddagen")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_ampm=True),
                         "12:15 PM")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=True),
                         "tolv femten")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=False),
                         "tolv femten")

        dt = datetime.datetime(2017, 1, 31, 19, 40, 49)
        self.assertEqual(nice_time(dt, lang="da-dk"), "syv fyrre")
        self.assertEqual(nice_time(dt, lang="da-dk", use_ampm=True),
                         "syv fyrre om aftenen")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False),
                         "07:40")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_ampm=True),
                         "07:40 PM")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="da-dk", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=True),
                         "nitten fyrre")
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True,
                                   use_ampm=False),
                         "nitten fyrre")

        dt = datetime.datetime(2017, 1, 31, 1, 15, 00)
        self.assertEqual(nice_time(dt, lang="da-dk", use_24hour=True),
                         "et femten")

        dt = datetime.datetime(2017, 1, 31, 1, 35, 00)
        self.assertEqual(nice_time(dt, lang="da-dk"),
                         "et femogtredive")

        dt = datetime.datetime(2017, 1, 31, 1, 45, 00)
        self.assertEqual(nice_time(dt, lang="da-dk"), "et femogfyrre")

        dt = datetime.datetime(2017, 1, 31, 4, 50, 00)
        self.assertEqual(nice_time(dt, lang="da-dk"), "fire halvtres")

        dt = datetime.datetime(2017, 1, 31, 5, 55, 00)
        self.assertEqual(nice_time(dt, lang="da-dk"), "fem femoghalvtres")

        dt = datetime.datetime(2017, 1, 31, 5, 30, 00)
        self.assertEqual(nice_time(dt, lang="da-dk", use_ampm=True),
                         "fem tredive om morgenen")


if __name__ == "__main__":
    unittest.main()
