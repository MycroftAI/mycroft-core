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


NUMBERS_FIXTURE_FR = {
    1.435634: '1,436',
    2: '2',
    5.0: '5',
    1234567890: '1234567890',
    12345.67890: '12345,679',
    0.027: '0,027',
    0.5: 'un demi',
    1.333: '1 et 1 tiers',
    2.666: '2 et 2 tiers',
    0.25: 'un quart',
    1.25: '1 et 1 quart',
    0.75: '3 quarts',
    1.75: '1 et 3 quarts',
    3.4: '3 et 2 cinquièmes',
    16.8333: '16 et 5 sixièmes',
    12.5714: '12 et 4 septièmes',
    9.625: '9 et 5 huitièmes',
    6.777: '6 et 7 neuvièmes',
    3.1: '3 et 1 dixième',
    2.272: '2 et 3 onzièmes',
    5.583: '5 et 7 douzièmes',
    8.384: '8 et 5 treizièmes',
    0.071: 'un quatorzième',
    6.466: '6 et 7 quinzièmes',
    8.312: '8 et 5 seizièmes',
    2.176: '2 et 3 dix-septièmes',
    200.722: '200 et 13 dix-huitièmes',
    7.421: '7 et 8 dix-neuvièmes',
    0.05: 'un vingtième'
}


class TestNiceNumberFormat_fr(unittest.TestCase):
    def test_convert_float_to_nice_number_fr(self):
        for number, number_str in NUMBERS_FIXTURE_FR.items():
            self.assertEqual(nice_number(number, lang="fr-fr"), number_str,
                             'should format {} as {} and not {}'.format(
                                 number, number_str, nice_number(
                                     number, lang="fr-fr")))

    def test_specify_denominator_fr(self):
        self.assertEqual(nice_number(5.5, lang="fr-fr",
                                     denominators=[1, 2, 3]),
                         '5 et demi',
                         'should format 5.5 as 5 et demi not {}'.format(
                             nice_number(5.5, lang="fr-fr",
                                         denominators=[1, 2, 3])))
        self.assertEqual(nice_number(2.333, lang="fr-fr",
                                     denominators=[1, 2]),
                         '2,333',
                         'should format 2.333 as 2,333 not {}'.format(
                             nice_number(2.333, lang="fr-fr",
                                         denominators=[1, 2])))

    def test_no_speech_fr(self):
        self.assertEqual(nice_number(6.777, lang="fr-fr", speech=False),
                         '6 7/9',
                         'should format 6.777 as 6 7/9 not {}'.format(
                             nice_number(6.777, lang="fr-fr", speech=False)))
        self.assertEqual(nice_number(6.0, lang="fr-fr", speech=False),
                         '6',
                         'should format 6.0 as 6 not {}'.format(
                             nice_number(6.0, lang="fr-fr", speech=False)))
        self.assertEqual(nice_number(1234567890, lang="fr-fr", speech=False),
                         '1 234 567 890',
                         'should format 1234567890 as'
                         '1 234 567 890 not {}'.format(
                             nice_number(1234567890, lang="fr-fr",
                                         speech=False)))
        self.assertEqual(nice_number(12345.6789, lang="fr-fr", speech=False),
                         '12 345,679',
                         'should format 12345.6789 as'
                         '12 345,679 not {}'.format(
                             nice_number(12345.6789, lang="fr-fr",
                                         speech=False)))


# def pronounce_number(number, lang="en-us", places=2):
class TestPronounceNumber_fr(unittest.TestCase):
    def test_convert_int_fr(self):
        self.assertEqual(pronounce_number(0, lang="fr-fr"), "zéro")
        self.assertEqual(pronounce_number(1, lang="fr-fr"), "un")
        self.assertEqual(pronounce_number(10, lang="fr-fr"), "dix")
        self.assertEqual(pronounce_number(15, lang="fr-fr"), "quinze")
        self.assertEqual(pronounce_number(20, lang="fr-fr"), "vingt")
        self.assertEqual(pronounce_number(27, lang="fr-fr"), "vingt-sept")
        self.assertEqual(pronounce_number(30, lang="fr-fr"), "trente")
        self.assertEqual(pronounce_number(33, lang="fr-fr"), "trente-trois")
        self.assertEqual(pronounce_number(71, lang="fr-fr"),
                         "soixante-et-onze")
        self.assertEqual(pronounce_number(80, lang="fr-fr"), "quatre-vingts")
        self.assertEqual(pronounce_number(74, lang="fr-fr"),
                         "soixante-quatorze")
        self.assertEqual(pronounce_number(79, lang="fr-fr"),
                         "soixante-dix-neuf")
        self.assertEqual(pronounce_number(91, lang="fr-fr"),
                         "quatre-vingt-onze")
        self.assertEqual(pronounce_number(97, lang="fr-fr"),
                         "quatre-vingt-dix-sept")
        self.assertEqual(pronounce_number(300, lang="fr-fr"), "300")

    def test_convert_negative_int_fr(self):
        self.assertEqual(pronounce_number(-1, lang="fr-fr"), "moins un")
        self.assertEqual(pronounce_number(-10, lang="fr-fr"), "moins dix")
        self.assertEqual(pronounce_number(-15, lang="fr-fr"), "moins quinze")
        self.assertEqual(pronounce_number(-20, lang="fr-fr"), "moins vingt")
        self.assertEqual(pronounce_number(-27, lang="fr-fr"),
                         "moins vingt-sept")
        self.assertEqual(pronounce_number(-30, lang="fr-fr"), "moins trente")
        self.assertEqual(pronounce_number(-33, lang="fr-fr"),
                         "moins trente-trois")

    def test_convert_decimals_fr(self):
        self.assertEqual(pronounce_number(1.234, lang="fr-fr"),
                         "un virgule deux trois")
        self.assertEqual(pronounce_number(21.234, lang="fr-fr"),
                         "vingt-et-un virgule deux trois")
        self.assertEqual(pronounce_number(21.234, lang="fr-fr", places=1),
                         "vingt-et-un virgule deux")
        self.assertEqual(pronounce_number(21.234, lang="fr-fr", places=0),
                         "vingt-et-un")
        self.assertEqual(pronounce_number(21.234, lang="fr-fr", places=3),
                         "vingt-et-un virgule deux trois quatre")
        self.assertEqual(pronounce_number(21.234, lang="fr-fr", places=4),
                         "vingt-et-un virgule deux trois quatre")
        self.assertEqual(pronounce_number(21.234, lang="fr-fr", places=5),
                         "vingt-et-un virgule deux trois quatre")
        self.assertEqual(pronounce_number(-1.234, lang="fr-fr"),
                         "moins un virgule deux trois")
        self.assertEqual(pronounce_number(-21.234, lang="fr-fr"),
                         "moins vingt-et-un virgule deux trois")
        self.assertEqual(pronounce_number(-21.234, lang="fr-fr", places=1),
                         "moins vingt-et-un virgule deux")
        self.assertEqual(pronounce_number(-21.234, lang="fr-fr", places=0),
                         "moins vingt-et-un")
        self.assertEqual(pronounce_number(-21.234, lang="fr-fr", places=3),
                         "moins vingt-et-un virgule deux trois quatre")
        self.assertEqual(pronounce_number(-21.234, lang="fr-fr", places=4),
                         "moins vingt-et-un virgule deux trois quatre")
        self.assertEqual(pronounce_number(-21.234, lang="fr-fr", places=5),
                         "moins vingt-et-un virgule deux trois quatre")


# def nice_time(dt, lang="en-us", speech=True, use_24hour=False,
#              use_ampm=False):
class TestNiceDateFormat_fr(unittest.TestCase):
    def test_convert_times_fr(self):
        dt = datetime.datetime(2017, 1, 31,
                               13, 22, 3)

        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "une heure vingt-deux")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_ampm=True),
                         "une heure vingt-deux de l'après-midi")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False),
                         "1:22")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_ampm=True),
                         "1:22 PM")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:22")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=True),
                         "treize heures vingt-deux")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=False),
                         "treize heures vingt-deux")

        dt = datetime.datetime(2017, 1, 31,
                               13, 0, 3)
        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "une heure")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_ampm=True),
                         "une heure de l'après-midi")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False),
                         "1:00")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_ampm=True),
                         "1:00 PM")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:00")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=True),
                         "treize heures")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=False),
                         "treize heures")

        dt = datetime.datetime(2017, 1, 31,
                               13, 2, 3)
        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "une heure deux")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_ampm=True),
                         "une heure deux de l'après-midi")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False),
                         "1:02")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_ampm=True),
                         "1:02 PM")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "13:02")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=True),
                         "treize heures deux")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=False),
                         "treize heures deux")

        dt = datetime.datetime(2017, 1, 31,
                               0, 2, 3)
        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "minuit deux")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_ampm=True),
                         "minuit deux")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False),
                         "12:02")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_ampm=True),
                         "12:02 AM")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "00:02")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=True),
                         "minuit deux")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=False),
                         "minuit deux")

        dt = datetime.datetime(2017, 1, 31,
                               12, 15, 9)
        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "midi et quart")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_ampm=True),
                         "midi et quart")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_ampm=True),
                         "12:15 PM")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=True),
                         "midi quinze")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=False),
                         "midi quinze")

        dt = datetime.datetime(2017, 1, 31,
                               19, 40, 49)
        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "huit heures moins vingt")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_ampm=True),
                         "huit heures moins vingt du soir")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False),
                         "7:40")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_ampm=True),
                         "7:40 PM")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="fr-fr", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=True),
                         "dix-neuf heures quarante")
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True,
                                   use_ampm=False),
                         "dix-neuf heures quarante")

        dt = datetime.datetime(2017, 1, 31,
                               1, 15, 00)
        self.assertEqual(nice_time(dt, lang="fr-fr", use_24hour=True),
                         "une heure quinze")

        dt = datetime.datetime(2017, 1, 31,
                               1, 35, 00)
        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "deux heures moins vingt-cinq")

        dt = datetime.datetime(2017, 1, 31,
                               1, 45, 00)
        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "deux heures moins le quart")

        dt = datetime.datetime(2017, 1, 31,
                               4, 50, 00)
        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "cinq heures moins dix")

        dt = datetime.datetime(2017, 1, 31,
                               5, 55, 00)
        self.assertEqual(nice_time(dt, lang="fr-fr"),
                         "six heures moins cinq")

        dt = datetime.datetime(2017, 1, 31,
                               5, 30, 00)
        self.assertEqual(nice_time(dt, lang="fr-fr", use_ampm=True),
                         "cinq heures et demi du matin")


if __name__ == "__main__":
    unittest.main()
