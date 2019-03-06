# -*- coding: utf-8 -*-
#
# Copyright 2019 Mycroft AI Inc.
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

from mycroft.util.format import nice_time
from mycroft.util.format import pronounce_number

NUMBERS_FIXTURE_PT = {
    1.435634: '1,436',
    2: '2',
    5.0: '5',
    0.027: '0,027',
    0.5: 'um meio',
    1.333: '1 e 1 terço',
    2.666: '2 e 2 terços',
    0.25: 'um quarto',
    1.25: '1 e 1 quarto',
    0.75: '3 quartos',
    1.75: '1 e 3 quartos',
    3.4: '3 e 2 quintos',
    16.8333: '16 e 5 sextos',
    12.5714: u'12 e 4 sétimos',
    9.625: '9 e 5 oitavos',
    6.777: '6 e 7 nonos',
    3.1: u'3 e 1 décimo',
    2.272: '2 e 3 onze avos',
    5.583: '5 e 7 doze avos',
    8.384: '8 e 5 treze avos',
    0.071: 'catorze avos',
    6.466: '6 e 7 quinze avos',
    8.312: '8 e 5 dezasséis avos',
    2.176: '2 e 3 dezassete avos',
    200.722: '200 e 13 dezoito avos',
    7.421: '7 e 8 dezanove avos',
    0.05: 'um vigésimo'

}


class TestPronounceNumber(unittest.TestCase):
    def test_convert_int(self):
        self.assertEqual(pronounce_number(0, lang="pt"), "zero")
        self.assertEqual(pronounce_number(1, lang="pt"), "um")
        self.assertEqual(pronounce_number(10, lang="pt"), "dez")
        self.assertEqual(pronounce_number(15, lang="pt"), "quinze")
        self.assertEqual(pronounce_number(21, lang="pt"), "vinte e um")
        self.assertEqual(pronounce_number(27, lang="pt"), "vinte e sete")
        self.assertEqual(pronounce_number(30, lang="pt"), "trinta")
        self.assertEqual(pronounce_number(19, lang="pt"), "dezanove")
        self.assertEqual(pronounce_number(88, lang="pt"), "oitenta e oito")
        self.assertEqual(pronounce_number(46, lang="pt"), "quarenta e seis")
        self.assertEqual(pronounce_number(99, lang="pt"), "noventa e nove")

    def test_convert_negative_int(self):
        self.assertEqual(pronounce_number(-1, lang="pt"), "menos um")
        self.assertEqual(pronounce_number(-10, lang="pt"), "menos dez")
        self.assertEqual(pronounce_number(-15, lang="pt"), "menos quinze")
        self.assertEqual(pronounce_number(-21, lang="pt"), "menos vinte e um")
        self.assertEqual(pronounce_number(-27, lang="pt"),
                         "menos vinte e sete")
        self.assertEqual(pronounce_number(-30, lang="pt"), "menos trinta")
        self.assertEqual(pronounce_number(-35, lang="pt"),
                         "menos trinta e cinco")
        self.assertEqual(pronounce_number(-83, lang="pt"),
                         "menos oitenta e três")
        self.assertEqual(pronounce_number(-19, lang="pt"), "menos dezanove")
        self.assertEqual(pronounce_number(-88, lang="pt"),
                         "menos oitenta e oito")
        self.assertEqual(pronounce_number(-46, lang="pt"),
                         "menos quarenta e seis")
        self.assertEqual(pronounce_number(-99, lang="pt"),
                         "menos noventa e nove")

    def test_convert_decimals(self):
        self.assertEqual(pronounce_number(1.234, lang="pt"),
                         "um vírgula dois três")
        self.assertEqual(pronounce_number(21.234, lang="pt"),
                         "vinte e um vírgula dois três")
        self.assertEqual(pronounce_number(21.234, lang="pt", places=1),
                         "vinte e um vírgula dois")
        self.assertEqual(pronounce_number(21.234, lang="pt", places=0),
                         "vinte e um")
        self.assertEqual(pronounce_number(21.234, lang="pt", places=3),
                         "vinte e um vírgula dois três quatro")
        self.assertEqual(pronounce_number(21.234, lang="pt", places=4),
                         "vinte e um vírgula dois três quatro")
        self.assertEqual(pronounce_number(20.234, lang="pt", places=5),
                         "vinte vírgula dois três quatro")
        self.assertEqual(pronounce_number(-21.234, lang="pt"),
                         "menos vinte e um vírgula dois três")
        self.assertEqual(pronounce_number(-21.234, lang="pt", places=1),
                         "menos vinte e um vírgula dois")
        self.assertEqual(pronounce_number(-21.234, lang="pt", places=0),
                         "menos vinte e um")
        self.assertEqual(pronounce_number(-21.234, lang="pt", places=3),
                         "menos vinte e um vírgula dois três quatro")
        self.assertEqual(pronounce_number(-21.234, lang="pt", places=4),
                         "menos vinte e um vírgula dois três quatro")
        self.assertEqual(pronounce_number(-21.234, lang="pt", places=5),
                         "menos vinte e um vírgula dois três quatro")


class TestNiceDateFormat(unittest.TestCase):
    def test_pm(self):
        dt = datetime.datetime(2017, 1, 31,
                               13, 22, 3)

        # Verify defaults haven't changed
        self.assertEqual(nice_time(dt, lang="pt-pt"),
                         nice_time(dt, "pt-pt", True, False, False))

        self.assertEqual(nice_time(dt, lang="pt"),
                         "uma e vinte e dois")
        self.assertEqual(nice_time(dt, lang="pt", use_ampm=True),
                         "uma e vinte e dois da tarde")
        self.assertEqual(nice_time(dt, lang="pt", speech=False), "1:22")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_ampm=True), "1:22 PM")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_24hour=True), "13:22")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_24hour=True, use_ampm=True), "13:22")
        self.assertEqual(nice_time(dt, lang="pt", use_24hour=True,
                                   use_ampm=True), "treze e vinte e dois")
        self.assertEqual(nice_time(dt, lang="pt", use_24hour=True,
                                   use_ampm=False), "treze e vinte e dois")

        dt = datetime.datetime(2017, 1, 31,
                               13, 0, 3)
        self.assertEqual(nice_time(dt, lang="pt"),
                         "uma em ponto")
        self.assertEqual(nice_time(dt, lang="pt", use_ampm=True),
                         "uma da tarde")
        self.assertEqual(nice_time(dt, lang="pt", speech=False),
                         "1:00")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_ampm=True), "1:00 PM")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_24hour=True), "13:00")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_24hour=True, use_ampm=True), "13:00")
        self.assertEqual(nice_time(dt, lang="pt", use_24hour=True,
                                   use_ampm=True), "treze")
        dt = datetime.datetime(2017, 1, 31,
                               13, 2, 3)
        self.assertEqual(nice_time(dt, lang="pt", use_24hour=True),
                         "treze e dois")
        self.assertEqual(nice_time(dt, lang="pt", use_ampm=True),
                         "uma e dois da tarde")
        self.assertEqual(nice_time(dt, lang="pt", speech=False),
                         "1:02")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_ampm=True), "1:02 PM")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_24hour=True), "13:02")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_24hour=True, use_ampm=True), "13:02")
        self.assertEqual(nice_time(dt, lang="pt", use_24hour=True,
                                   use_ampm=True), "treze e dois")
        self.assertEqual(nice_time(dt, lang="pt", use_24hour=True,
                                   use_ampm=False), "treze e dois")

    def test_midnight(self):
        dt = datetime.datetime(2017, 1, 31,
                               0, 2, 3)
        self.assertEqual(nice_time(dt, lang="pt"),
                         "meia noite e dois")
        self.assertEqual(nice_time(dt, lang="pt", use_ampm=True),
                         "meia noite e dois")
        self.assertEqual(nice_time(dt, lang="pt", use_24hour=True),
                         "zero e dois")
        self.assertEqual(nice_time(dt, lang="pt", speech=False),
                         "12:02")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_ampm=True), "12:02 AM")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_24hour=True), "00:02")
        self.assertEqual(nice_time(dt, lang="pt", speech=False,
                                   use_24hour=True,
                                   use_ampm=True), "00:02")
        self.assertEqual(nice_time(dt, lang="pt", use_24hour=True,
                                   use_ampm=True), "zero e dois")
        self.assertEqual(nice_time(dt, lang="pt", use_24hour=True,
                                   use_ampm=False), "zero e dois")

    def test_midday(self):
        dt = datetime.datetime(2017, 1, 31,
                               12, 15, 9)
        self.assertEqual(nice_time(dt, lang="pt-pt"),
                         "meio dia e um quarto")
        self.assertEqual(nice_time(dt, lang="pt-pt", use_ampm=True),
                         "meio dia e um quarto")
        self.assertEqual(nice_time(dt, lang="pt-pt", speech=False),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="pt-pt", speech=False,
                                   use_ampm=True),
                         "12:15 PM")
        self.assertEqual(nice_time(dt, lang="pt-pt", speech=False,
                                   use_24hour=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="pt-pt", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "12:15")
        self.assertEqual(nice_time(dt, lang="pt-pt", use_24hour=True,
                                   use_ampm=True),
                         "doze e quinze")
        self.assertEqual(nice_time(dt, lang="pt-pt", use_24hour=True,
                                   use_ampm=False),
                         "doze e quinze")

    def test_minutes_to_hour(self):
        # "twenty minutes to midnight"
        dt = datetime.datetime(2017, 1, 31,
                               19, 40, 49)
        self.assertEqual(nice_time(dt, lang="pt-pt"),
                         "oito menos vinte")
        self.assertEqual(nice_time(dt, lang="pt-pt", use_ampm=True),
                         "oito menos vinte da tarde")
        self.assertEqual(nice_time(dt, lang="pt-pt", speech=False),
                         "7:40")
        self.assertEqual(nice_time(dt, lang="pt-pt", speech=False,
                                   use_ampm=True),
                         "7:40 PM")
        self.assertEqual(nice_time(dt, lang="pt-pt", speech=False,
                                   use_24hour=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="pt-pt", speech=False,
                                   use_24hour=True, use_ampm=True),
                         "19:40")
        self.assertEqual(nice_time(dt, lang="pt-pt", use_24hour=True,
                                   use_ampm=True),
                         "dezanove e quarenta")
        self.assertEqual(nice_time(dt, lang="pt-pt", use_24hour=True,
                                   use_ampm=False),
                         "dezanove e quarenta")

    def test_minutes_past_hour(self):
        # "quarter past ten"
        dt = datetime.datetime(2017, 1, 31,
                               1, 15, 00)
        self.assertEqual(nice_time(dt, lang="pt-pt", use_24hour=True),
                         "uma e quinze")
        self.assertEqual(nice_time(dt, lang="pt-pt"),
                         "uma e um quarto")

        dt = datetime.datetime(2017, 1, 31,
                               1, 35, 00)
        self.assertEqual(nice_time(dt, lang="pt-pt"),
                         "duas menos vinte e cinco")

        dt = datetime.datetime(2017, 1, 31,
                               1, 45, 00)
        self.assertEqual(nice_time(dt, lang="pt-pt"),
                         "duas menos um quarto")

        dt = datetime.datetime(2017, 1, 31,
                               4, 50, 00)
        self.assertEqual(nice_time(dt, lang="pt-pt"),
                         "cinco menos dez")

        dt = datetime.datetime(2017, 1, 31,
                               5, 55, 00)
        self.assertEqual(nice_time(dt, lang="pt-pt"),
                         "seis menos cinco")

        dt = datetime.datetime(2017, 1, 31,
                               5, 30, 00)
        self.assertEqual(nice_time(dt, lang="pt-pt", use_ampm=True),
                         "cinco e meia da madrugada")

        dt = datetime.datetime(2017, 1, 31,
                               23, 15, 9)
        self.assertEqual(nice_time(dt, lang="pt-pt", use_24hour=True,
                                   use_ampm=True),
                         "vinte e três e quinze")
        self.assertEqual(nice_time(dt, lang="pt-pt", use_24hour=False,
                                   use_ampm=True),
                         "onze e um quarto da noite")


if __name__ == "__main__":
    unittest.main()
