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
from datetime import datetime, time

from mycroft.util.parse import extract_datetime
from mycroft.util.parse import extract_number
from mycroft.util.parse import normalize

LANG = "nl-nl"


class TestParsing(unittest.TestCase):
    def test_articles(self):
        self.assertEqual(
            normalize("dit is de test", LANG, remove_articles=True),
            "dit is test")
        self.assertEqual(
            normalize("en nog een Test", LANG, remove_articles=True),
            "en nog 1 Test")
        self.assertEqual(normalize("dit is de Extra-Test", LANG,
                                   remove_articles=False),
                         "dit is de Extra-Test")

    def test_extract_number(self):
        self.assertEqual(extract_number("dit is de eerste Test",
                                        lang=LANG, ordinals=True), 1)
        self.assertEqual(extract_number("dit is 2 Test", lang=LANG), 2)
        self.assertEqual(extract_number("dit is tweede Test", lang=LANG,
                                        ordinals=True),
                         2)
        self.assertEqual(
            extract_number("dit is Test drie", lang=LANG), 3)
        self.assertEqual(
            extract_number("dit is de Test Nummer 4", lang=LANG), 4)
        self.assertEqual(extract_number("één derde kopje",
                                        lang=LANG), 1.0 / 3.0)
        self.assertEqual(extract_number("drie kopjes", lang=LANG), 3)
        self.assertEqual(extract_number("1/3 kopje", lang=LANG), 1.0 / 3.0)
        self.assertEqual(extract_number("een kwart kopje", lang=LANG),
                         0.25)
        self.assertEqual(extract_number("1/4 kopje", lang=LANG), 0.25)
        self.assertEqual(extract_number("kwart kopje", lang=LANG), 0.25)
        self.assertEqual(extract_number("2/3 kopje", lang=LANG), 2.0 / 3.0)
        self.assertEqual(extract_number("3/4 kopje", lang=LANG), 3.0 / 4.0)
        self.assertEqual(extract_number("1 en 3/4 kopje", lang=LANG),
                         1.75)
        self.assertEqual(extract_number("1 kopje en een half",
                                        lang=LANG), 1.5)
        self.assertEqual(extract_number("anderhalf kopje",
                                        lang=LANG), 1.5)
        self.assertEqual(extract_number("driekwart kopje", lang=LANG),
                         3.0 / 4.0)
        self.assertEqual(extract_number("driekwart kopje", lang=LANG),
                         3.0 / 4.0)

    def test_extractdatetime_nl(self):
        def extractWithFormat(text):
            date = datetime(2017, 6, 27, 0, 0)
            [extractedDate, leftover] = extract_datetime(text, date,
                                                         LANG, )
            extractedDate = extractedDate.strftime("%Y-%m-%d %H:%M:%S")
            return [extractedDate, leftover]

        def testExtract(text, expected_date, expected_leftover):
            res = extractWithFormat(text)
            self.assertEqual(res[0], expected_date)
            self.assertEqual(res[1], expected_leftover)

        testExtract("zet een alarm voor 1 dag na vandaag",
                    "2017-06-28 00:00:00", "zet een alarm")
        testExtract("laten we om 8:00 's avonds afspreken",
                    "2017-06-27 20:00:00", "laten we afspreken")
        testExtract("zet een alarm voor 5 dagen na vandaag",
                    "2017-07-02 00:00:00", "zet een alarm")
        testExtract("wat voor weer is het overmorgen?",
                    "2017-06-29 00:00:00", "wat voor weer is")
        testExtract("herinner me om 10:45 's avonds",
                    "2017-06-27 22:45:00", "herinner me")
        testExtract("Hoe is het weer morgen",
                    "2017-06-28 00:00:00", "hoe is weer")
        testExtract("3 december",
                    "2017-12-03 00:00:00", "")
        testExtract("hoe is het weer vandaag", "2017-06-27 00:00:00",
                    "hoe is weer")
        testExtract("herinner me over 5 jaar aan mijn contract",
                    "2022-06-27 00:00:00", "herinner me aan mijn contract")
        testExtract("hoe is het weer volgende week vrijdag",
                    "2017-06-30 00:00:00", "hoe is weer")
        testExtract("herinner me mijn moeder te bellen op 7 september",
                    "2017-09-07 00:00:00", "herinner me mijn moeder te bellen")
        testExtract("hoe is het weer 3 dagen na vandaag",
                    "2017-06-30 00:00:00", "hoe is weer")
        testExtract(
            "herinner me vanavond aan het ophalen van mijn kinderen",
            "2017-06-27 19:00:00",
            "herinner me aan ophalen van mijn kinderen")
        testExtract(
            "Herinner me mijn moeder te bellen over 8 weken en 2 dagen",
            "2017-08-24 00:00:00", "herinner me mijn moeder te bellen")

        testExtract("Speel rick astley 2 dagen na vrijdag",
                    "2017-07-02 00:00:00", "speel rick astley")
        testExtract("plan een afspraak in de nacht van 3 september",
                    "2017-09-03 00:00:00", "plan een afspraak")

        testExtract("hoe is het weer morgenavond", "2017-06-28 19:00:00",
                    "hoe is weer")
        testExtract("hoe is het weer woensdagavond", "2017-06-28 19:00:00",
                    "hoe is weer")
        testExtract("hoe is het weer dinsdagochtend", "2017-06-27 08:00:00",
                    "hoe is weer")
        testExtract("plan een afspraak in voor donderdagmiddag",
                    "2017-06-29 15:00:00", "plan een afspraak")
        testExtract("Wat voor weer wordt het vrijdagochtend",
                    "2017-06-30 08:00:00", "wat voor weer wordt")

        # TODO these fail altogether
        # testExtract("laten we vanavond om 8:00 uur afspreken",
        #             "2017-06-27 20:00:00", "laten we afspreken")
        # testExtract(
        #     "wordt er regen verwacht op maandag om 3 uur 's middags", "", "")
        # testExtract("plan een afspraak in voor maandagmiddag 4 uur",
        #             "2017-07-03 16:00:00", "plan een afspraak")
        # testExtract("plan een afspraak om 2 uur 's middags",
        #             "2017-06-27 14:00:00", "plan een afspraak")

    def test_extractdatetime_default_nl(self):
        default = time(9, 0, 0)
        anchor = datetime(2019, 11, 1, 0, 0)
        res = extract_datetime("laten we afspreken op donderdag",
                               anchor, lang=LANG, default_time=default)
        self.assertEqual(default, res[0].time())

    def test_spaces(self):
        self.assertEqual(normalize("  dit   is  een    test", LANG),
                         "dit is 1 test")
        self.assertEqual(normalize("  dit   is  een    test  ",
                                   LANG), "dit is 1 test")

    def test_numbers(self):
        self.assertEqual(
            normalize("dit is een twee drie test", LANG),
            "dit is 1 2 3 test")
        self.assertEqual(
            normalize("dit is vier vijf zes test", LANG),
            "dit is 4 5 6 test")
        self.assertEqual(
            normalize("dit is zeven acht negen test", LANG),
            "dit is 7 8 9 test")
        self.assertEqual(
            normalize("dit is zeven acht negen test", LANG),
            "dit is 7 8 9 test")
        self.assertEqual(
            normalize("dit is tien elf twaalf test", LANG),
            "dit is 10 11 12 test")
        self.assertEqual(
            normalize("dit is dertien veertien test", LANG),
            "dit is 13 14 test")
        self.assertEqual(
            normalize(u"dit is vijftien zestien zeventien", LANG),
            "dit is 15 16 17")
        self.assertEqual(
            normalize("dit is achttien negentien twintig", LANG),
            "dit is 18 19 20")


if __name__ == "__main__":
    unittest.main()
