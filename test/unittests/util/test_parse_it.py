# -*- coding: utf-8  -*-
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

from mycroft.util.parse import get_gender
from mycroft.util.parse import extract_datetime
from mycroft.util.parse import extractnumber
from mycroft.util.parse import normalize


class TestNormalize(unittest.TestCase):
    """
        Test cases for Italian parsing
    """
    def test_articles_it(self):
        self.assertEqual(normalize(u"questo è il test",
                                   lang="it", remove_articles=True),
                         u"questo è test")
        self.assertEqual(normalize(u"questa è la frase",
                                   lang="it", remove_articles=True),
                         u"questa è frase")
        self.assertEqual(normalize(u"questo è lo scopo", lang="it",
                                   remove_articles=True),
                         u"questo è scopo")
        self.assertEqual(normalize(u"questo è il test extra",
                                   lang="it", remove_articles=False),
                         u"questo è il test extra")

    def test_extractnumber_it(self):
        self.assertEqual(extractnumber(u"questo è il primo test",
                                       lang="it"), 1)
        self.assertEqual(extractnumber(u"questo è il 2 test",
                                       lang="it"), 2)
        self.assertEqual(extractnumber(u"questo è il secondo test",
                                       lang="it"), 2)
        self.assertEqual(extractnumber(u"questo è un terzo di test",
                                       lang="it"), 1.0 / 3.0)
        self.assertEqual(extractnumber(u"questo è test numero 4",
                                       lang="it"), 4)
        self.assertEqual(extractnumber("un terzo di tazza",
                                       lang="it"), 1.0 / 3.0)
        self.assertEqual(extractnumber("tre tazze",
                                       lang="it"), 3)
        self.assertEqual(extractnumber("1/3 tazze",
                                       lang="it"), 1.0 / 3.0)
        self.assertEqual(extractnumber("un quarto di tazza",
                                       lang="it"), 0.25)
        self.assertEqual(extractnumber("1/4 tazza",
                                       lang="it"), 0.25)
        self.assertEqual(extractnumber("2/3 tazza",
                                       lang="it"), 2.0 / 3.0)
        self.assertEqual(extractnumber("3/4 tazza",
                                       lang="it"), 3.0 / 4.0)
        self.assertEqual(extractnumber("1 e 1/4 tazza",
                                       lang="it"), 1.25)
        self.assertEqual(extractnumber("1 tazza e mezzo",
                                       lang="it"), 1.5)
        self.assertEqual(extractnumber("una tazza e mezzo",
                                       lang="it"), 1.5)
        self.assertEqual(extractnumber("una e mezza tazza",
                                       lang="it"), 1.5)
        self.assertEqual(extractnumber("una e una mezza tazza",
                                       lang="it"), 1.5)
        self.assertEqual(extractnumber("tre quarti tazza",
                                       lang="it"), 3.0 / 4.0)
        self.assertEqual(extractnumber("tre quarto tazza",
                                       lang="it"), 3.0 / 4.0)
        self.assertEqual(extractnumber("sette punto cinque",
                                       lang="it"), 7.5)
        self.assertEqual(extractnumber("sette punto 5",
                                       lang="it"), 7.5)
        self.assertEqual(extractnumber("sette e mezzo",
                                       lang="it"), 7.5)
        self.assertEqual(extractnumber("sette e ottanta",
                                       lang="it"), 7.80)
        self.assertEqual(extractnumber("sette e otto",
                                       lang="it"), 7.8)
        self.assertEqual(extractnumber("sette e zero otto",
                                       lang="it"), 7.08)
        self.assertEqual(extractnumber("sette e zero zero otto",
                                       lang="it"), 7.008)
        self.assertEqual(extractnumber("venti tredicesimi",
                                       lang="it"), 20.0 / 13.0)
        self.assertEqual(extractnumber("sei virgola sessanta sei",
                                       lang="it"), 6.66)
        self.assertEqual(extractnumber("sei virgola sessantasei",
                                       lang="it"), 6.66)
        self.assertEqual(extractnumber("seicento sessanta  sei",
                                       lang="it"), 666)
        self.assertEqual(extractnumber("seicento punto zero sei",
                                       lang="it"), 600.06)
        self.assertEqual(extractnumber("seicento punto zero zero sei",
                                       lang="it"), 600.006)
        self.assertEqual(extractnumber("seicento punto zero zero zero sei",
                                       lang="it"), 600.0006)
        self.assertEqual(extractnumber("tre decimi ",
                                       lang="it"), 0.30000000000000004)
        self.assertEqual(extractnumber("dodici centesimi",
                                       lang="it"), 0.12)
        self.assertEqual(extractnumber("cinque e quaranta due millesimi",
                                       lang="it"), 5.042)
        self.assertEqual(extractnumber("mille e uno",
                                       lang="it"), 1001)
        self.assertEqual(extractnumber("due mila venti due dollari ",
                                       lang="it"), 2022)
        self.assertEqual(extractnumber(
            "cento quattordici mila quattrocento undici dollari ",
            lang="it"), 114411)
        self.assertEqual(extractnumber("ventitre dollari ", lang="it"), 23)
        self.assertEqual(extractnumber("quarantacinque minuti ",
                                       lang="it"), 45)
        self.assertEqual(extractnumber("ventuno anni ",
                                       lang="it"), 21)
        self.assertEqual(extractnumber("ventotto euro ",
                                       lang="it"), 28)
        self.assertEqual(extractnumber("dodici e quarantacinque ",
                                       lang="it"), 12.45)
        self.assertEqual(extractnumber("quarantotto euro ",
                                       lang="it"), 48)
        self.assertEqual(extractnumber("novantanove euro ",
                                       lang="it"), 99)
        self.assertEqual(extractnumber("avvisa se qualcuno arriva ",
                                       lang="it"), False)

    def test_spaces_it(self):
        self.assertEqual(normalize(u"questo   e'  il    test",
                                   lang="it"), u"questo e' test")
        self.assertEqual(normalize(u"questo   è    un    test  ",
                                   lang="it"), u"questo è 1 test")
        self.assertEqual(normalize(u"un  altro test  ",
                                   lang="it"), u"1 altro test")
        self.assertEqual(normalize(u"questa è un'  altra amica   ", lang="it",
                                   remove_articles=False),
                         u"questa è 1 altra amica")
        self.assertEqual(normalize(u"questo   è  un    test   ", lang="it",
                                   remove_articles=False), u"questo è 1 test")

    def test_numbers_it(self):
        self.assertEqual(normalize(u"questo è il test uno due tre",
                                   lang="it"), u"questo è test 1 2 3")
        self.assertEqual(normalize(u"è un test sette otto nove",
                                   lang="it"), u"è 1 test 7 8 9")
        self.assertEqual(normalize("test zero dieci undici dodici tredici",
                                   lang="it"), "test 0 10 11 12 13")
        self.assertEqual(normalize("test mille seicento sessanta e sei",
                                   lang="it", remove_articles=False),
                         "test 1000 600 60 e 6")
        self.assertEqual(normalize("test sette e mezzo",
                                   lang="it", remove_articles=False),
                         "test 7 e mezzo")
        self.assertEqual(normalize("test due punto nove",
                                   lang="it"), "test 2 punto 9")
        self.assertEqual(normalize("test cento e nove",
                                   lang="it", remove_articles=False),
                         "test 100 e 9")
        self.assertEqual(normalize("test venti e 1",
                                   lang="it"), "test 20 e 1")
        self.assertEqual(normalize("test ventuno e ventisette",
                                   lang="it"), "test 21 e 27")

    def test_extractdatetime_it(self):
        def extractWithFormat(text):
            date = datetime(2018, 01, 13, 00, 00)
            [extractedDate, leftover] = extract_datetime(text, date,
                                                         lang="it")
            extractedDate = extractedDate.strftime("%Y-%m-%d %H:%M:%S")
            return [extractedDate, leftover]

        def testExtract(text, expected_date, expected_leftover):
            res = extractWithFormat(text)
            self.assertEqual(res[0], expected_date)
            self.assertEqual(res[1], expected_leftover)

        testExtract(u"quale giorno è oggi",
                    "2018-01-13 00:00:00", u"quale giorno")
        testExtract(u"che giorno è domani",
                    "2018-01-14 00:00:00", u"che giorno")
        testExtract(u"che giorno era ieri",
                    "2018-01-12 00:00:00", u"che giorno")
        testExtract(u"che giorno è dopo domani",
                    "2018-01-15 00:00:00", u"che giorno")
        testExtract(u"fissare la cena tra 5 giorni",
                    "2018-01-18 00:00:00", u"fissare cena")
        testExtract(u"Come è il tempo per dopodomani",
                    "2018-01-15 00:00:00", u"come tempo")
        testExtract(u"ricordami alle 22:45",
                    "2018-01-13 22:45:00", u"ricordami")
        testExtract(u"Come è il tempo venerdì mattina",
                    "2018-01-19 08:00:00", "come tempo")
        testExtract(u"Ricordami di chiamare la mamma"
                    u" in 8 settimane e 2 giorni.",
                    "2018-03-12 00:00:00", u"ricordami chiamare mamma")
        testExtract(u"Gioca a briscola 2 giorni dopo venerdì",
                    "2018-01-21 00:00:00", u"gioca briscola")
        testExtract(u"Inizia le pulizie alle 15:45 di giovedì",
                    "2018-01-18 15:45:00", u"inizia pulizie")
        testExtract("lunedi compra formaggio",
                    "2018-01-15 00:00:00", u"compra formaggio")
        testExtract("suona musica compleanno tra 5 anni da oggi",
                    "2023-01-13 00:00:00", "suona musica compleanno")
        testExtract(u"Invia Skype alla mamma alle 12:45 di giovedì prossimo.",
                    "2018-01-18 12:45:00", u"invia skype mamma")
        testExtract(u"Come è il tempo questo venerdì?",
                    "2018-01-19 00:00:00", u"come tempo")
        testExtract(u"Come è il tempo questo venerdì pomeriggio?",
                    "2018-01-19 15:00:00", u"come tempo")
        testExtract(u"Come è il tempo questo venerdì a mezza notte?",
                    "2018-01-20 00:00:00", u"come tempo")
        testExtract(u"Come è il tempo questo venerdì a mezzogiorno?",
                    "2018-01-19 12:00:00", "come tempo")
        testExtract(u"Come è il tempo questo venerdì alle 11 del mattino?",
                    "2018-01-19 11:00:00", "come tempo")
        testExtract("Ricordami di chiamare mia madre il 3 agosto.",
                    "2018-08-03 00:00:00", "ricordami chiamare mia madre")
        testExtract(u"comprare fragole il 13 maggio",
                    "2018-05-13 00:00:00", "comprare fragole")
        testExtract(u"fare acquisti il 13 maggio",
                    "2018-05-13 00:00:00", "fare acquisti")
        testExtract(u"compra le candele il 1° maggio",
                    "2018-05-01 00:00:00", "compra candele")
        testExtract(u"bere birra il 13 maggio",
                    "2018-05-13 00:00:00", "bere birra")
        testExtract(u"Come è il tempo 1 giorno dopo domani?",
                    "2018-01-15 00:00:00", "come tempo")
        testExtract(u"Come è il tempo alle ore 0700?",
                    "2018-01-13 07:00:00", "come tempo ora")
        testExtract(u"Come è il tempo domani alle 7 in punto?",
                    "2018-01-14 07:00:00", "come tempo")
        testExtract(u"Come è il tempo domani alle 2 del pomeriggio",
                    "2018-01-14 14:00:00", "come tempo")
        testExtract(u"Come è il tempo domani pomeriggio alle 2",
                    "2018-01-14 14:00:00", "come tempo")
        testExtract(u"Come è il tempo domani per le 2:00",
                    "2018-01-14 02:00:00", "come tempo")
        testExtract(u"Come è il tempo alle 2 del pomeriggio di \
                    venerdì prossimo?",
                    "2018-01-19 14:00:00", u"come tempo")
        testExtract(u"Ricordami di svegliarmi tra 4 anni",
                    "2022-01-13 00:00:00", u"ricordami svegliarmi")
        testExtract(u"Ricordami di svegliarmi tra 4 anni e 4 giorni",
                    "2022-01-17 00:00:00", u"ricordami svegliarmi")
        testExtract(u"Dormi 3 giorni da domani.",
                    "2018-01-17 00:00:00", u"dormi")
        testExtract(u"segna appuntamento tra 2 settimane e 6 giorni \
                    dopo sabato",
                    "2018-02-02 00:00:00", u"segna appuntamento")
        testExtract(u"La festa inizia alle 8 di sera di giovedì",
                    "2018-01-18 20:00:00", u"la festa inizia")
        testExtract(u"Come è il meteo 3 tra giorni?",
                    "2018-01-16 00:00:00", u"come meteo")
        testExtract(u"fissa appuntamento dicembre 3",
                    "2018-12-03 00:00:00", "fissa appuntamento")
        testExtract(u"incontriamoci questa sera alle 8 ",
                    "2018-01-13 20:00:00", "incontriamoci")
        testExtract(u"incontriamoci alle 8 questa sera",
                    "2018-01-13 20:00:00", "incontriamoci")
        testExtract(u"impostare sveglia questa sera alle 9 ",
                    "2018-01-13 21:00:00", "impostare sveglia")
        testExtract(u"impostare sveglia questa sera alle 21 ",
                    "2018-01-13 21:00:00", "impostare sveglia")
        testExtract(u"inserire appuntamento domani sera alle 23",
                    "2018-01-14 23:00:00", "inserire appuntamento")
        testExtract(u"inserire appuntamento domani alle 9 e mezza",
                    "2018-01-14 09:30:00", "inserire appuntamento")
        testExtract(u"inserire appuntamento domani sera alle 23 e 3 quarti",
                    "2018-01-14 23:45:00", "inserire appuntamento")

    def test_gender_it(self):
        self.assertEqual(get_gender("mucca", lang="it"), "f")
        self.assertEqual(get_gender("cavallo", lang="it"), "m")
        self.assertEqual(get_gender("mucche", "le mucche", lang="it"), "f")
        self.assertEqual(get_gender("bue", "il bue mangia la erba",
                                    lang="it"), "m")
        self.assertEqual(get_gender("pesce", "il pesce nuota",
                                    lang="it"), "m")
        self.assertEqual(get_gender("tigre", lang="it"), "f")
        self.assertEqual(get_gender("uomini", "questi uomini mangiano pasta",
                                    lang="it"), "m")
        self.assertEqual(get_gender("ponte", "il ponte", lang="it"), "m")
        self.assertEqual(get_gender("ponte", u"questo ponte è caduto",
                                    lang="it"), "m")
        self.assertEqual(get_gender("scultrice", "questa scultrice famosa",
                                    lang="it"), "f")
        self.assertEqual(get_gender("scultore", "questo scultore famoso",
                                    lang="it"), "m")
        self.assertEqual(get_gender("scultori", "gli scultori rinascimentali",
                                    lang="it"), "m")
        self.assertEqual(get_gender("scultrici", "le scultrici moderne",
                                    lang="it"), "f")


if __name__ == "__main__":
    unittest.main()
