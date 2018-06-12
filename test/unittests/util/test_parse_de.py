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
from datetime import datetime

from mycroft.util.parse import extract_datetime
from mycroft.util.parse import extractnumber
from mycroft.util.parse import normalize


class TestNormalize(unittest.TestCase):
    def test_articles(self):
        self.assertEqual(
            normalize("dies ist der test", lang="de-de", remove_articles=True),
            "dies ist test")
        self.assertEqual(
            normalize("und noch ein Test", lang="de-de", remove_articles=True),
            "und noch 1 Test")
        self.assertEqual(normalize("dies ist der Extra-Test", lang="de-de",
                                   remove_articles=False),
                         "dies ist der Extra-Test")

    def test_extractnumber(self):
        self.assertEqual(extractnumber("dies ist der erste Test",
                                       lang="de-de"), 1)
        self.assertEqual(extractnumber("dies ist 2 Test", lang="de-de"), 2)
        self.assertEqual(extractnumber("dies ist zweiter Test", lang="de-de"),
                         2)
        self.assertEqual(
            extractnumber("dies ist der dritte Test", lang="de-de"), 3)
        self.assertEqual(
            extractnumber("dies ist der Test Nummer 4", lang="de-de"), 4)
        self.assertEqual(extractnumber("ein drittel einer Tasse",
                                       lang="de-de"), 1.0 / 3.0)
        self.assertEqual(extractnumber("drei Tassen", lang="de-de"), 3)
        self.assertEqual(extractnumber("1/3 Tasse", lang="de-de"), 1.0 / 3.0)
        self.assertEqual(extractnumber("eine viertel Tasse", lang="de-de"),
                         0.25)
        self.assertEqual(extractnumber("1/4 Tasse", lang="de-de"), 0.25)
        self.assertEqual(extractnumber("viertel Tasse", lang="de-de"), 0.25)
        self.assertEqual(extractnumber("2/3 Tasse", lang="de-de"), 2.0 / 3.0)
        self.assertEqual(extractnumber("3/4 Tasse", lang="de-de"), 3.0 / 4.0)
        self.assertEqual(extractnumber("1 und 3/4 Tassen", lang="de-de"), 1.75)
        self.assertEqual(extractnumber("1 Tasse und eine halbe", lang="de-de"),
                         1.5)
        self.assertEqual(
            extractnumber("eine Tasse und eine halbe", lang="de-de"), 1.5)
        self.assertEqual(
            extractnumber("eine und eine halbe Tasse", lang="de-de"), 1.5)
        self.assertEqual(extractnumber("ein und ein halb Tassen",
                                       lang="de-de"), 1.5)
        self.assertEqual(extractnumber("drei Viertel Tasse", lang="de-de"),
                         3.0 / 4.0)
        self.assertEqual(extractnumber("drei Viertel Tassen", lang="de-de"),
                         3.0 / 4.0)

    def test_extractdatetime_de(self):
        def extractWithFormat(text):
            date = datetime(2017, 6, 27, 0, 0)
            [extractedDate, leftover] = extract_datetime(text, date,
                                                         lang="de-de", )
            extractedDate = extractedDate.strftime("%Y-%m-%d %H:%M:%S")
            return [extractedDate, leftover]

        def testExtract(text, expected_date, expected_leftover):
            res = extractWithFormat(text)
            self.assertEqual(res[0], expected_date)
            self.assertEqual(res[1], expected_leftover)

        testExtract(u"setze den frisörtermin auf 5 tage von heute",
                    "2017-07-02 00:00:00", u"setze frisörtermin")
        testExtract(u"wie ist das wetter übermorgen?",
                    "2017-06-29 00:00:00", "wie ist das wetter")
        testExtract("erinnere mich um 10:45 abends",
                    "2017-06-27 22:45:00", "erinnere mich")
        testExtract("was ist das Wetter am freitag morgen",
                    "2017-06-30 08:00:00", "was ist das wetter")
        testExtract("wie ist das wetter morgen",
                    "2017-06-28 00:00:00", "wie ist das wetter")
        testExtract(
            "erinnere mich meine mutter anzurufen in 8 Wochen und 2 Tagen",
            "2017-08-24 00:00:00", "erinnere mich meine mutter anzurufen")
        testExtract("spiele rick astley musik 2 tage von freitag",
                    "2017-07-02 00:00:00", "spiele rick astley musik")
        testExtract("starte die invasion um 3:45 pm am Donnerstag",
                    "2017-06-29 15:45:00", "starte die invasion")
        testExtract(u"am montag bestelle kuchen von der bäckerei",
                    "2017-07-03 00:00:00", u"bestelle kuchen von bäckerei")
        testExtract("spiele happy birthday musik 5 jahre von heute",
                    "2022-06-27 00:00:00", "spiele happy birthday musik")
        testExtract(u"skype mama um 12:45 pm nächsten Donnerstag",
                    "2017-07-06 12:45:00", "skype mama")
        testExtract(u"wie ist das wetter nächsten donnerstag?",
                    "2017-07-06 00:00:00", "wie ist das wetter")
        testExtract(u"wie ist das Wetter nächsten Freitag morgen",
                    "2017-07-07 08:00:00", "wie ist das wetter")
        testExtract(u"wie ist das wetter nächsten freitag abend",
                    "2017-07-07 19:00:00", "wie ist das wetter")
        testExtract("wie ist das wetter nächsten freitag nachmittag",
                    "2017-07-07 15:00:00", "wie ist das wetter")
        testExtract(u"erinnere mich mama anzurufen am dritten august",
                    "2017-08-03 00:00:00", "erinnere mich mama anzurufen")
        testExtract("kaufe feuerwerk am einundzwanzigsten juli",
                    "2017-07-21 00:00:00", "kaufe feuerwerk")
        testExtract(u"wie ist das wetter 2 wochen ab nächsten freitag",
                    "2017-07-21 00:00:00", "wie ist das wetter")
        testExtract("wie ist das wetter am mittwoch um 07:00",
                    "2017-06-28 07:00:00", "wie ist das wetter")
        testExtract("wie ist das wetter am mittwoch um 7 uhr",
                    "2017-06-28 07:00:00", "wie ist das wetter")
        testExtract("Mache einen Termin um 12:45 pm nächsten donnerstag",
                    "2017-07-06 12:45:00", "mache einen termin")
        testExtract("wie ist das wetter an diesem donnerstag?",
                    "2017-06-29 00:00:00", "wie ist das wetter")
        testExtract("vereinbare den besuch für 2 wochen und 6 tage ab samstag",
                    "2017-07-21 00:00:00", "vereinbare besuch")
        testExtract("beginne die invasion um 03:45 am donnerstag",
                    "2017-06-29 03:45:00", "beginne die invasion")
        testExtract("beginne die invasion um 3 uhr nachts am donnerstag",
                    "2017-06-29 03:00:00", "beginne die invasion")
        testExtract("beginne die invasion um 8 Uhr am donnerstag",
                    "2017-06-29 08:00:00", "beginne die invasion")
        testExtract("starte die party um 8 uhr abends am donnerstag",
                    "2017-06-29 20:00:00", "starte die party")
        testExtract("starte die invasion um 8 abends am donnerstag",
                    "2017-06-29 20:00:00", "starte die invasion")
        testExtract("starte die invasion am donnerstag um mittag",
                    "2017-06-29 12:00:00", "starte die invasion")
        testExtract("starte die invasion am donnerstag um mitternacht",
                    "2017-06-29 00:00:00", "starte die invasion")
        testExtract("starte die invasion am donnerstag um 5 uhr",
                    "2017-06-29 05:00:00", "starte die invasion")
        testExtract("erinnere mich aufzuwachen in 4 jahren",
                    "2021-06-27 00:00:00", "erinnere mich aufzuwachen")
        testExtract("erinnere mich aufzuwachen in 4 jahren und 4 tagen",
                    "2021-07-01 00:00:00", "erinnere mich aufzuwachen")
        testExtract("wie ist das wetter 3 Tage nach morgen?",
                    "2017-07-01 00:00:00", "wie ist das wetter")
        testExtract("dritter dezember",
                    "2017-12-03 00:00:00", "")
        testExtract("lass uns treffen um 8:00 abends",
                    "2017-06-27 20:00:00", "lass uns treffen")

    def test_spaces(self):
        self.assertEqual(normalize("  dies   ist  ein    test", lang="de-de"),
                         "dies ist 1 test")
        self.assertEqual(normalize("  dies   ist  ein    test  ",
                                   lang="de-de"), "dies ist 1 test")

    def test_numbers(self):
        self.assertEqual(
            normalize("dies ist eins zwei drei test", lang="de-de"),
            "dies ist 1 2 3 test")
        self.assertEqual(
            normalize(u"es ist vier fünf sechs test", lang="de-de"),
            "es ist 4 5 6 test")
        self.assertEqual(
            normalize("es ist sieben acht neun test", lang="de-de"),
            "es ist 7 8 9 test")
        self.assertEqual(
            normalize("es ist sieben acht neun test", lang="de-de"),
            "es ist 7 8 9 test")
        self.assertEqual(
            normalize(u"dies ist zehn elf zwölf test", lang="de-de"),
            "dies ist 10 11 12 test")
        self.assertEqual(
            normalize("dies ist dreizehn vierzehn test", lang="de-de"),
            "dies ist 13 14 test")
        self.assertEqual(
            normalize(u"dies ist fünfzehn sechzehn siebzehn", lang="de-de"),
            "dies ist 15 16 17")
        self.assertEqual(
            normalize("dies ist achtzehn neunzehn zwanzig", lang="de-de"),
            "dies ist 18 19 20")


if __name__ == "__main__":
    unittest.main()
