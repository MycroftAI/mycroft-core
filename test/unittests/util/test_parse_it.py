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
from datetime import datetime, time

from mycroft.util.parse import get_gender
from mycroft.util.parse import extract_datetime
from mycroft.util.parse import extract_number, extract_numbers
from mycroft.util.parse import normalize


class TestNormalize(unittest.TestCase):
    """
        Test cases for Italian parsing
    """
    def test_articles_it(self):
        """
        Test cases for Italian remove_articles
        """
        self.assertEqual(normalize('questo è il test',
                                   lang='it', remove_articles=True),
                         'questo è test')
        self.assertEqual(normalize('questa è la frase',
                                   lang='it', remove_articles=True),
                         'questa è frase')
        self.assertEqual(normalize('questo è lo scopo', lang='it',
                                   remove_articles=True),
                         'questo è scopo')
        self.assertEqual(normalize('questo è il test extra',
                                   lang='it', remove_articles=False),
                         'questo è il test extra')

    def test_extractnumber_it(self):
        """
        Test cases for Italian extract_number, lang='it'
        """
        self.assertEqual(extract_number('questo è il primo test',
                                        lang='it'), 1)
        self.assertEqual(extract_number('questo è il 2 test', lang='it'), 2)
        self.assertEqual(extract_number('questo è il secondo test',
                                        lang='it', ordinals=True), 2)
        self.assertEqual(extract_number('questo è un terzo di test',
                                        lang='it'), 1.0 / 3.0)
        self.assertEqual(extract_number('questo è il terzo test',
                                        lang='it', ordinals=True), 3.0)
        self.assertEqual(extract_number('questo è il trentaseiesimo test',
                                        lang='it'), 36.0)
        self.assertEqual(extract_number('questo è il test numero 4',
                                        lang='it'), 4)
        self.assertEqual(extract_number('una tazza', lang='it'), 1)
        self.assertEqual(extract_number('un gatto', lang='it'), 1)
        self.assertEqual(extract_number('un terzo di tazza',
                                        lang='it'), 1.0 / 3.0)
        self.assertEqual(extract_number('2 quinti di tazza', lang='it'), 0.4)
        self.assertEqual(extract_number('due quinti di tazza', lang='it'), 0.4)
        self.assertEqual(extract_number('tre tazze', lang='it'), 3)
        self.assertEqual(extract_number('1/3 tazze', lang='it'), 1.0 / 3.0)
        self.assertEqual(extract_number('un quarto di tazza', lang='it'), 0.25)
        self.assertEqual(extract_number('1/4 tazza', lang='it'), 0.25)
        self.assertEqual(extract_number('2/3 tazza', lang='it'), 2.0 / 3.0)
        self.assertEqual(extract_number('3/4 tazza', lang='it'), 3.0 / 4.0)
        self.assertEqual(extract_number('1 e 1/4 tazza', lang='it'), 1.25)
        self.assertEqual(extract_number('1 tazza e mezzo', lang='it'), 1.5)
        self.assertEqual(extract_number('una tazza e mezzo', lang='it'), 1.5)
        self.assertEqual(extract_number('una e mezza tazza', lang='it'), 1.5)
        self.assertEqual(extract_number('una e una mezza tazza',
                                        lang='it'), 1.5)
        self.assertEqual(extract_number('tre quarti di tazza',
                                        lang='it'), 3.0 / 4.0)
        self.assertEqual(extract_number('ventidue', lang='it'), 22)
        self.assertEqual(extract_number('duecento', lang='it'), 200)
        self.assertEqual(extract_number('novemila', lang='it'), 9000)
        self.assertEqual(extract_number('duemilioni',
                                        lang='it',
                                        short_scale=False), 2000000)
        self.assertEqual(extract_number('duemilionicinquecentomila '
                                        'tonnellate di metallo',
                                        lang='it'), 2500000)
        self.assertEqual(extract_number('duemilioni cinquecentomila '
                                        'tonnellate di metallo',
                                        lang='it'), 2500000)
        self.assertEqual(extract_number('sei trilioni',
                                        lang='it'), 6000000000000000000.0)
        self.assertEqual(extract_number('sei trilioni', short_scale=True,
                                        lang='it'), 6e+18)
        self.assertEqual(extract_number('unmiliardounmilione',
                                        lang='it',
                                        short_scale=False), 1001000000)
        self.assertEqual(extract_number('unmiliardocento',
                                        lang='it',
                                        short_scale=False), 1000000100)
        self.assertEqual(extract_number('duemiliardiunmilionecentotrentadue',
                                        lang='it'), 2001000132)
        self.assertEqual(extract_number('venti diciassettesimi',
                                        lang='it'), 20.0/17.0)
        self.assertEqual(extract_number('uno punto cinque', lang='it'), 1.5)
        self.assertEqual(extract_number('tre punto quattordici',
                                        lang='it'), 3.14)
        self.assertEqual(extract_number('zero punto due', lang='it'), 0.2)
        self.assertEqual(extract_number('vecchio miliardi di anni',
                                        lang='it'), 1000000000.0)
        self.assertEqual(extract_number('vecchio trilioni di anni',
                                        short_scale=False,
                                        lang='it'), 1000000000000000000.0)
        self.assertEqual(extract_number('centomila', lang='it'), 100000)
        self.assertEqual(extract_number('millequattrocentonovantadue',
                                        lang='it'), 1492)
        self.assertEqual(extract_number('meno 2', lang='it'), -2)
        self.assertEqual(extract_number('meno settanta', lang='it'), -70)
        self.assertEqual(extract_number('mille milioni',
                                        lang='it'), 1000000000)
        self.assertEqual(extract_number('millecentouno',
                                        lang='it'), 1101)
        self.assertEqual(extract_number('un sesto terzo',
                                        lang='it'), 1 / 6 / 3)
        self.assertEqual(extract_number('trenta secondi', lang='it'), 30)
        self.assertEqual(extract_number('trenta secondi', lang='it',
                                        ordinals=True), 30)
        self.assertEqual(extract_number('sette e qualcosa', lang='it'), 7.0)
        self.assertEqual(extract_number('sette punto 5', lang='it'), 7.5)
        self.assertEqual(extract_number('sette punto 575', lang='it'), 7.575)
        self.assertEqual(extract_number('sette e mezzo', lang='it'), 7.5)
        self.assertEqual(extract_number('sette e ottanta', lang='it'), 7.80)
        self.assertEqual(extract_number('sette e otto', lang='it'), 7.8)
        self.assertEqual(extract_number('sette e zero otto',
                                        lang='it'), 7.08)
        self.assertEqual(extract_number('sette e zero zero zero otto gradi',
                                        lang='it'), 7.0008)
        self.assertEqual(extract_number('venti tredicesimi',
                                        lang='it'), 20.0 / 13.0)
        self.assertEqual(extract_number('venti tredicesimi', lang='it',
                                        short_scale=True), 20.0 / 13.0)
        self.assertEqual(extract_number('sei virgola sessantasei',
                                        lang='it'), 6.66)
        self.assertEqual(extract_number('sei virgola sessantasei',
                                        lang='it'), 6.66)
        self.assertEqual(extract_number('seicentosessantasei',
                                        lang='it'), 666)
        self.assertEqual(extract_number('seicento sessantasei',
                                        lang='it'), 666)
        self.assertEqual(extract_number('mille quattrocento novantadue',
                                        lang='it'), 1492)
        self.assertEqual(extract_number('millequattrocentonovantadue',
                                        lang='it'), 1492)
        self.assertEqual(extract_number('sei cento punto zero sei',
                                        lang='it'), 600.06)
        self.assertEqual(extract_number('seicento punto zero zero sei',
                                        lang='it'), 600.006)
        self.assertEqual(extract_number('seicento punto zero zero zero sei',
                                        lang='it'), 600.0006)
        self.assertEqual(extract_number('tre decimi ',
                                        lang='it'), 0.30000000000000004)
        self.assertEqual(extract_number('dodici centesimi',
                                        lang='it'), 0.12)
#        self.assertEqual(extract_number('cinque e quarantadue millesimi',
#                                        lang='it'), 5.042)
        self.assertEqual(extract_number('milleuno',
                                        lang='it'), 1001)
        self.assertEqual(extract_number('due mila ventidue dollari ',
                                        lang='it'), 2022)
        self.assertEqual(extract_number(
            'centoquattordicimilaquattrocentoundici dollari ',
            lang='it', ordinals=True, short_scale=True), 114411)
        self.assertEqual(extract_number('ventitre dollari ', lang='it'), 23)
        self.assertEqual(extract_number('ventuno anni ',
                                        lang='it'), 21)
        self.assertEqual(extract_number('dodici e quarantacinque ',
                                        lang='it'), 12.45)
        self.assertEqual(extract_number('avvisa se qualcuno arriva ',
                                        lang='it'), False)
        self.assertTrue(extract_number('Il giocatore di tennis è veloce',
                                       lang='it') is False)
        self.assertTrue(extract_number('nessuno', lang='it') is False)
        self.assertTrue(extract_number('fraggle zero',
                                       lang='it') is not False)
        self.assertEqual(extract_number('fraggle zero', lang='it'), 0)
        self.assertTrue(extract_number('grobo 0', lang='it') is not False)
        self.assertEqual(extract_number('grobo 0', lang='it'), 0)
        self.assertEqual(extract_number('un paio di birre', lang='it'), 2)
        self.assertEqual(extract_number('un centinaio di birre',
                                        lang='it'), 100)
        self.assertEqual(extract_number('un paio di migliaia di birre',
                                        lang='it'), 2000)
        self.assertEqual(extract_number('una decina di monete',
                                        lang='it'), 10)
        self.assertEqual(extract_number('tre dozzine di uova',
                                        lang='it'), 36)
        self.assertEqual(extract_number('zero gatti',
                                        lang='it'), 0)

    def test_extractdatetime_it_not_normalized(self):
        """
        Test cases for Italian datetime parsing

        """
        def extractWithFormat_it(text):
            date = datetime(2018, 1, 13, 13, 4)  # Sab 13 Gen, 2018 @ 13:04
            [extractedDate, leftover] = extract_datetime(text, date,
                                                         lang='it-it')
            extractedDate = extractedDate.strftime('%Y-%m-%d %H:%M:%S')
            return [extractedDate, leftover]

        def testExtract_it(text, expected_date, expected_leftover):
            res = extractWithFormat_it(normalize(text))  # era normalize(text)
            self.assertEqual(res[0], expected_date, 'per=' + text)
            self.assertEqual(res[1], expected_leftover, 'per=' + text)

        testExtract_it('che ore sono adesso',
                       '2018-01-13 13:04:00', 'che ora sono')
        testExtract_it('tra due secondi',
                       '2018-01-13 13:04:02', '')
        testExtract_it('fra un minuto',
                       '2018-01-13 13:05:00', '')
        testExtract_it('tra un paio di minuti',
                       '2018-01-13 13:06:00', '')
        testExtract_it('tra un paio di ore',
                       '2018-01-13 15:04:00', '')
        testExtract_it('tra due settimane',
                       '2018-01-27 00:00:00', '')
        testExtract_it('fra un paio di mesi',
                       '2018-03-13 00:00:00', '')
        testExtract_it('tra un paio di anni',
                       '2020-01-13 00:00:00', '')
        testExtract_it('tra un decennio',
                       '2028-01-13 00:00:00', '')
        testExtract_it('fra un paio di decenni',
                       '2038-01-13 00:00:00', '')
        testExtract_it('nel prossimo decennio',
                       '2028-01-13 00:00:00', '')
        testExtract_it('nel decennio prossimo',
                       '2028-01-13 00:00:00', '')
        testExtract_it('nello scorso decennio',
                       '2008-01-13 00:00:00', '')
        testExtract_it('nel decennio passato',
                       '2008-01-13 00:00:00', '')
        testExtract_it('tra un secolo',
                       '2118-01-13 00:00:00', '')
        testExtract_it('fra un millennio',
                       '3018-01-13 00:00:00', '')
        testExtract_it('tra un paio di decenni',
                       '2038-01-13 00:00:00', '')
        testExtract_it('tra 5 decenni',
                       '2068-01-13 00:00:00', '')
        testExtract_it('fra un paio di secoli',
                       '2218-01-13 00:00:00', '')
        testExtract_it('tra 2 secoli',
                       '2218-01-13 00:00:00', '')
        testExtract_it('fra un paio di millenni',
                       '4018-01-13 00:00:00', '')
        testExtract_it('appuntamento tra un ora',
                       '2018-01-13 14:04:00', 'appuntamento')
        # testExtract_it('lo voglio entro l\'ora',
        #                '2018-01-13 14:04:00', 'lo voglio entro')
        testExtract_it('in 1 secondo',
                       '2018-01-13 13:04:01', '')
        testExtract_it('tra 2 secondi',
                       '2018-01-13 13:04:02', '')
        testExtract_it('Imposta l\'imboscata tra 1 minuto',
                       '2018-01-13 13:05:00', 'imposta imboscata')
        testExtract_it('Imposta l\'imboscata tra mezzora',
                       '2018-01-13 13:34:00', 'imposta imboscata')
        testExtract_it('imposta l\'imboscata tra 5 giorni da oggi',
                       '2018-01-18 00:00:00', 'imposta imboscata')
        testExtract_it('quali sono previsioni meteo di dopo domani?',
                       '2018-01-15 00:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali sono previsioni meteo dopo il prossimo giovedi?',
                       '2018-01-18 00:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali erano previsioni meteo dopo lo scorso giovedi?',
                       '2018-01-11 00:00:00', 'quali erano previsioni '
                       'meteo dopo')
        testExtract_it('quali sono previsioni meteo dopo giovedi prossimo?',
                       '2018-01-25 00:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali erano previsioni meteo dopo giovedi scorso?',
                       '2018-01-11 00:00:00', 'quali erano previsioni meteo')
        testExtract_it('quali erano previsioni meteo da adesso?',
                       '2018-01-13 00:00:00', 'quali erano previsioni meteo')
        testExtract_it('ricordami alle 10:45 pm',
                       '2018-01-13 22:45:00', 'ricordami')
        testExtract_it('quale è il meteo di venerdì mattina',
                       '2018-01-19 08:00:00', 'quale meteo')
        testExtract_it('quale è il meteo di domani',
                       '2018-01-14 00:00:00', 'quale meteo')
        testExtract_it('quali sono le previsioni meteo di oggi pomeriggio',
                       '2018-01-13 15:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali sono le previsioni meteo di oggi pomeriggio '
                       'presto',
                       '2018-01-13 14:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali sono le previsioni meteo di questa sera',
                       '2018-01-13 19:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali sono le previsioni meteo di questa sera tardi',
                       '2018-01-13 20:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali sono le previsioni meteo di mezzogiorno',
                       '2018-01-14 12:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali sono le previsioni meteo di mezzanotte',
                       '2018-01-14 00:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali sono le previsioni meteo di mezzo giorno',
                       '2018-01-14 12:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali sono le previsioni meteo di mezza notte',
                       '2018-01-14 00:00:00', 'quali sono previsioni meteo')
        testExtract_it('quali sono le previsioni meteo di questa mattina',
                       '2018-01-14 08:00:00', 'quali sono previsioni meteo')
        testExtract_it('ricordami di chiamare mamma il 3 agosto',
                       '2018-08-03 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami domani di chiamare mamma alle 7 del mattino',
                       '2018-01-14 07:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 7 di sera',
                       '2018-01-13 19:00:00', 'ricordami chiamare mamma')
        testExtract_it('chiamare mamma tra un ora',
                       '2018-01-13 14:04:00', 'chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 0600',
                       '2018-01-14 06:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 09 e 30',
                       '2018-01-13 21:30:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 7 in punto',
                       '2018-01-13 19:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma questa sera alle 7 '
                       'in punto',
                       '2018-01-13 19:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 7 questa sera',
                       '2018-01-13 19:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma domani alle 7 in punto'
                       ' del mattino',
                       '2018-01-14 07:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma giovedi sera '
                       'alle 7 in punto',
                       '2018-01-18 19:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma giovedi '
                       'mattina alle 7 in punto',
                       '2018-01-18 07:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 7 '
                       'in punto di giovedi mattina',
                       '2018-01-18 07:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 7:00 '
                       'di giovedi mattina',
                       '2018-01-18 07:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 7:00 di giovedi sera',
                       '2018-01-18 19:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 11:00 di '
                       'giovedi sera',
                       '2018-01-18 23:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 2:00 di giovedi '
                       'notte',
                       '2018-01-18 02:00:00', 'ricordami chiamare mamma notte')
        testExtract_it('ricordami di chiamare mamma alle 2:00 di giovedi '
                       'pomeriggio',
                       '2018-01-18 14:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma mercoledì sera alle 8',
                       '2018-01-17 20:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra due ore',
                       '2018-01-13 15:04:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra quindici minuti',
                       '2018-01-13 13:19:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra mezzora',
                       '2018-01-13 13:34:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra un quarto di ora',
                       '2018-01-13 13:19:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra tre quarti di ora',
                       '2018-01-13 13:49:00', 'ricordami chiamare mamma')
        testExtract_it('Play Rick Astley music 2 giorni da venerdì',
                       '2018-01-21 00:00:00', 'play rick astley music')
        testExtract_it('Iniziare l\'invasione alle 3:45 pm di giovedì',
                       '2018-01-18 15:45:00', 'iniziare invasione')
        testExtract_it('di lunedì, ordinare la torta pasticceria',
                       '2018-01-15 00:00:00', 'ordinare torta pasticceria')
        testExtract_it('Play Happy Birthday music 5 anni da oggi',
                       '2023-01-13 00:00:00', 'play happy birthday music')
        testExtract_it('comprare fuochi d\'artificio il 4 di luglio',
                       '2018-07-04 00:00:00', 'comprare fuochi d\'artificio')
        testExtract_it('quale è il meteo 2 settimane dopo il prossimo venerdì',
                       '2018-02-02 00:00:00', 'quale meteo')
        testExtract_it('quale è il meteo mercoledì alle ore 0700 ',
                       '2018-01-17 07:00:00', 'quale meteo')
        testExtract_it('Fissa la visita tra 2 settimane e 6 giorni da sabato',
                       '2018-02-02 00:00:00', 'fissa visita')
        testExtract_it('iniziare l\'invasione giovedì alle 03 45',
                       '2018-01-18 03:45:00', 'iniziare invasione')
        testExtract_it('iniziare l\'invasione alle 800 di giovedì',
                       '2018-01-18 08:00:00', 'iniziare invasione')
        testExtract_it('iniziare la festa alle 8 in punto della sera'
                       ' di giovedi',
                       '2018-01-18 20:00:00', 'iniziare festa')
        testExtract_it('iniziare l\'invasione alle 8 della sera di giovedì',
                       '2018-01-18 20:00:00', 'iniziare invasione')
        testExtract_it('iniziare l\'invasione di giovedi a mezzogiorno',
                       '2018-01-18 12:00:00', 'iniziare invasione')
        testExtract_it('iniziare l\'invasione di giovedi a mezzanotte',
                       '2018-01-19 00:00:00', 'iniziare invasione')
        testExtract_it('iniziare l\'invasione di giovedi alle 0500',
                       '2018-01-18 05:00:00', 'iniziare invasione')
        testExtract_it('remind me to wake up tra 4 anni',
                       '2022-01-13 00:00:00', 'remind me to wake up')
        testExtract_it('remind me to wake up tra 4 anni e 4 giorni',
                       '2022-01-17 00:00:00', 'remind me to wake up')
        testExtract_it('quali le previsioni meteo 3 giorni dopo domani?',
                       '2018-01-17 00:00:00', 'quali previsioni meteo')
        testExtract_it('il dicembre 3',
                       '2018-12-03 00:00:00', '')
        testExtract_it('nel 3 dicembre',
                       '2018-12-03 00:00:00', '')
        testExtract_it('il dic 3 2019',
                       '2019-12-03 00:00:00', '')
        testExtract_it('il 3 feb 2019',
                       '2019-02-03 00:00:00', '')
        testExtract_it('incontriamoci alle 8:00 questa sera',
                       '2018-01-13 20:00:00', 'incontriamoci')
        testExtract_it('incontriamoci alle 5 pm',
                       '2018-01-13 17:00:00', 'incontriamoci')
        testExtract_it('incontriamoci alle 8 a.m.',
                       '2018-01-14 08:00:00', 'incontriamoci')
        testExtract_it('ricordami di svegliarmi alle 8 a.m',
                       '2018-01-14 08:00:00', 'ricordami svegliarmi')
        testExtract_it('come è il tempo di giovedi',
                       '2018-01-18 00:00:00', 'come tempo')
        testExtract_it('come è il tempo di lunedi',
                       '2018-01-15 00:00:00', 'come tempo')
        testExtract_it('quale è il tempo di questo mercoledì',
                       '2018-01-17 00:00:00', 'quale tempo')
        testExtract_it('per giovedi quale è il meteo',
                       '2018-01-18 00:00:00', 'quale meteo')
        testExtract_it('questo giovedi quale è il meteo',
                       '2018-01-18 00:00:00', 'quale meteo')
        testExtract_it('lo scorso lunedi quale era il meteo',
                       '2018-01-08 00:00:00', 'quale meteo')
        testExtract_it('imposta un avviso per mercoledi sera alle 8',
                       '2018-01-17 20:00:00', 'imposta avviso')
        testExtract_it('imposta un avviso per mercoledi alle 3 in punto'
                       ' del pomeriggio',
                       '2018-01-17 15:00:00', 'imposta avviso')
        testExtract_it('imposta un avviso per mercoledi alle 3 in punto del'
                       ' mattino',
                       '2018-01-17 03:00:00', 'imposta avviso')
        testExtract_it('imposta una sveglia per mercoledi mattina alle'
                       ' 7 in punto',
                       '2018-01-17 07:00:00', 'imposta una sveglia')
        testExtract_it('imposta una sveglia per oggi alle 7 in punto',
                       '2018-01-13 19:00:00', 'imposta una sveglia')
        testExtract_it('imposta una sveglia per questa sera alle 7 in punto',
                       '2018-01-13 19:00:00', 'imposta una sveglia')
        testExtract_it('imposta una sveglia per questa sera alle 07:00',
                       '2018-01-13 19:00:00', 'imposta una sveglia')
        testExtract_it('nella sera del 5 giugno 2017 ricordami di' +
                       ' chiamare mia madre',
                       '2017-06-05 19:00:00', 'ricordami chiamare mia madre')
        testExtract_it('aggiorna il mio calendario per un meeting al mattino' +
                       ' con Giulio il 4 marzo',
                       '2018-03-04 08:00:00',
                       'aggiorna mio calendario meeting con giulio')
        testExtract_it('quale giorno è oggi',
                       '2018-01-13 00:00:00', 'quale giorno')
        testExtract_it('che giorno è domani',
                       '2018-01-14 00:00:00', 'che giorno')
        testExtract_it('che giorno era ieri',
                       '2018-01-12 00:00:00', 'che giorno')
        testExtract_it('che giorno è dopo domani',
                       '2018-01-15 00:00:00', 'che giorno')
        testExtract_it('fissare la cena tra 5 giorni',
                       '2018-01-18 00:00:00', 'fissare cena')
        testExtract_it('Come è il tempo per dopodomani',
                       '2018-01-15 00:00:00', 'come tempo')
        testExtract_it('ricordami alle 22:45',
                       '2018-01-13 22:45:00', 'ricordami')
        testExtract_it('Come è il tempo venerdì mattina',
                       '2018-01-19 08:00:00', 'come tempo')
        testExtract_it('ricordami di chiamare mamma giovedi prossimo',
                       '2018-01-25 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra 3 settimane',
                       '2018-02-03 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra 8 settimane',
                       '2018-03-10 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra 8 settimane'
                       ' e 2 giorni',
                       '2018-03-12 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra 4 giorni',
                       '2018-01-17 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra 3 mesi',
                       '2018-04-13 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra 2 anni e 2 giorni',
                       '2020-01-15 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma la prossima settimana',
                       '2018-01-20 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma la settimana prossima',
                       '2018-01-20 00:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di controllare spese della settimana scorsa',
                       '2018-01-06 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di controllare spese della scorsa settimana',
                       '2018-01-06 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di controllare spese del mese scorso',
                       '2017-12-13 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di controllare spese dello scorso mese',
                       '2017-12-13 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di controllare spese del mese prossimo',
                       '2018-02-13 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di controllare spese dello prossimo mese',
                       '2018-02-13 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di controllare spese dell anno scorso',
                       '2017-01-13 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di controllare spese dello scorso anno',
                       '2017-01-13 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di controllare spese del anno prossimo',
                       '2019-01-13 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di controllare spese dello prossimo anno',
                       '2019-01-13 00:00:00', 'ricordami controllare spese')
        testExtract_it('ricordami di telefonare giovedì prossimo',
                       '2018-01-25 00:00:00', 'ricordami telefonare')
        testExtract_it('ricordami di telefonare il prossimo giovedì',
                       '2018-01-25 00:00:00', 'ricordami telefonare')
        testExtract_it('ricordami di controllare spese di giovedi scorso',
                       '2018-01-11 00:00:00', 'ricordami controllare spese')
        testExtract_it('Gioca a briscola 2 giorni dopo venerdì',
                       '2018-01-21 00:00:00', 'gioca briscola')
        testExtract_it('Inizia le pulizie alle 15:45 di giovedì',
                       '2018-01-18 15:45:00', 'inizia pulizie')
        testExtract_it('lunedi compra formaggio',
                       '2018-01-15 00:00:00', 'compra formaggio')
        testExtract_it('suona musica compleanno tra 5 anni da oggi',
                       '2023-01-13 00:00:00', 'suona musica compleanno')
        testExtract_it('Invia Skype alla mamma alle 12:45 di giovedì'
                       ' prossimo.',
                       '2018-01-25 12:45:00', 'invia skype mamma')
        testExtract_it('Come è il tempo questo venerdì?',
                       '2018-01-19 00:00:00', 'come tempo')
        testExtract_it('Come è il tempo questo venerdì pomeriggio?',
                       '2018-01-19 15:00:00', 'come tempo')
        testExtract_it('Come è il tempo questo venerdì a mezza notte?',
                       '2018-01-20 00:00:00', 'come tempo')
        testExtract_it('Come è il tempo questo venerdì a mezzogiorno?',
                       '2018-01-19 12:00:00', 'come tempo')
        testExtract_it('Ricordami di chiamare mia madre il 3 agosto.',
                       '2018-08-03 00:00:00', 'ricordami chiamare mia madre')
        testExtract_it('compra le candele il 1° maggio',
                       '2018-05-01 00:00:00', 'compra candele')
        testExtract_it('Come è il tempo 1 giorno dopo domani?',
                       '2018-01-15 00:00:00', 'come tempo')
        testExtract_it('Come è il tempo alle ore 7?',
                       '2018-01-13 19:00:00', 'come tempo')
        testExtract_it('Come è il tempo domani alle 7 in punto?',
                       '2018-01-14 07:00:00', 'come tempo')
        testExtract_it('Come è il tempo domani alle 2 del pomeriggio',
                       '2018-01-14 14:00:00', 'come tempo')
        testExtract_it('Come è il tempo domani pomeriggio alle 2',
                       '2018-01-14 14:00:00', 'come tempo')
        testExtract_it('Come è il tempo domani per le 2:00',
                       '2018-01-14 02:00:00', 'come tempo')
        testExtract_it('Come è il tempo alle 2 del pomeriggio di '
                       'venerdì prossimo?',
                       '2018-01-26 14:00:00', 'come tempo')
        testExtract_it('Ricordami di svegliarmi tra 4 anni',
                       '2022-01-13 00:00:00', 'ricordami svegliarmi')
        testExtract_it('Ricordami di svegliarmi tra 4 anni e 4 giorni',
                       '2022-01-17 00:00:00', 'ricordami svegliarmi')
        testExtract_it('Dormi 3 giorni da domani.',
                       '2018-01-17 00:00:00', 'dormi')
        testExtract_it('segna appuntamento tra 2 settimane e 6 giorni '
                       'dopo sabato',
                       '2018-02-02 00:00:00', 'segna appuntamento')
        testExtract_it('La festa inizia alle 8 di sera di giovedì',
                       '2018-01-18 20:00:00', 'festa inizia')
        testExtract_it('Come è il meteo 3 tra giorni?',
                       '2018-01-16 00:00:00', 'come meteo')
        testExtract_it('fissa appuntamento dicembre 3',
                       '2018-12-03 00:00:00', 'fissa appuntamento')
        testExtract_it('incontriamoci questa sera alle 8 ',
                       '2018-01-13 20:00:00', 'incontriamoci')
        testExtract_it('incontriamoci alle 8 questa sera',
                       '2018-01-13 20:00:00', 'incontriamoci')
        testExtract_it('impostare sveglia questa sera alle 9 ',
                       '2018-01-13 21:00:00', 'impostare sveglia')
        testExtract_it('impostare sveglia questa sera alle 21 ',
                       '2018-01-13 21:00:00', 'impostare sveglia')
        testExtract_it('inserire appuntamento domani sera alle 23',
                       '2018-01-14 23:00:00', 'inserire appuntamento')
        testExtract_it('inserire appuntamento domani alle 9 e mezza',
                       '2018-01-14 09:30:00', 'inserire appuntamento')
        testExtract_it('inserire appuntamento domani sera alle 23 e 3 quarti',
                       '2018-01-14 23:45:00', 'inserire appuntamento')
        testExtract_it('inserire appuntamento domani sera alle 23 e 5 quarti',
                       '2018-01-14 23:00:00', 'inserire appuntamento')

    def test_extractdatetime_it_normalized(self):
        """
        Test cases for Italian datetime parsing

        """

        def extractWithFormat_it(text):
            date = datetime(2018, 1, 13, 13, 4)  # Sab 13 Gen, 2018 @ 13:04
            [extractedDate, leftover] = extract_datetime(text, date,
                                                         lang='it-it')
            extractedDate = extractedDate.strftime('%Y-%m-%d %H:%M:%S')
            return [extractedDate, leftover]

        def testExtract_it(text, expected_date, expected_leftover):
            res = extractWithFormat_it(normalize(text, lang='it-it'))
            self.assertEqual(res[0], expected_date, 'per=' + text)
            self.assertEqual(res[1], expected_leftover, 'per=' + text)

        testExtract_it('ricordami di chiamare mamma tra 15 minuti',
                       '2018-01-13 13:19:00', 'ricordami chiamare mamma')
        testExtract_it('chiamare mamma alle 17 e 30',
                       '2018-01-13 17:30:00', 'chiamare mamma')
        testExtract_it('ricordami di chiamare mamma tra 15 minuti',
                       '2018-01-13 13:19:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma sabato alle 10 ' +
                       'del mattino',
                       '2018-01-13 10:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 10 del mattino di'
                       ' questo sabato',
                       '2018-01-13 10:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 10 del mattino di'
                       ' sabato prossimo',
                       '2018-01-20 10:00:00', 'ricordami chiamare mamma')
        testExtract_it('ricordami di chiamare mamma alle 10 del mattino del'
                       ' prossimo sabato',
                       '2018-01-20 10:00:00', 'ricordami chiamare mamma')
        testExtract_it('Come è il tempo questo venerdì alle 11 del mattino?',
                       '2018-01-19 11:00:00', 'come tempo')
        testExtract_it('comprare fragole il 13 maggio',
                       '2018-05-13 00:00:00', 'comprare fragole')
        testExtract_it('inserire appuntamento domani sera alle 23 e' +
                       ' tre quarti',
                       '2018-01-14 23:45:00', 'inserire appuntamento')

    def test_extract_ambiguous_time_it(self):
        mattina = datetime(2017, 6, 27, 8, 1, 2)
        sera = datetime(2017, 6, 27, 20, 1, 2)
        mezzogiorno = datetime(2017, 6, 27, 12, 1, 2)
        self.assertEqual(
            extract_datetime('dai da mangiare ai pesci alle 10 in punto',
                             mattina, lang='it-it')[0],
            datetime(2017, 6, 27, 10, 0, 0))
        self.assertEqual(
            extract_datetime('dai da mangiare ai pesci alle 10 in punto',
                             mezzogiorno, lang='it-it')[0],
            datetime(2017, 6, 27, 22, 0, 0))
        self.assertEqual(
            extract_datetime('dai da mangiare ai pesci alle 10 in punto',
                             sera, lang='it-it')[0],
            datetime(2017, 6, 27, 22, 0, 0))

    def test_extract_relativedatetime_it(self):
        """
        Test cases for relative datetime
        """
        def extractWithFormat(text):
            date = datetime(2017, 6, 27, 10, 1, 2)
            [extractedDate, leftover] = extract_datetime(text, date,
                                                         lang='it-it')
            extractedDate = extractedDate.strftime('%Y-%m-%d %H:%M:%S')
            return [extractedDate, leftover]

        def testExtract_it(text, expected_date, expected_leftover):
            res = extractWithFormat(normalize(text))
            self.assertEqual(res[0], expected_date, 'per =' + text)
            self.assertEqual(res[1], expected_leftover, 'per =' + text)

        testExtract_it('incontriamoci tra 5 minuti',
                       '2017-06-27 10:06:02', 'incontriamoci')
        testExtract_it('incontriamoci tra 5 secondi',
                       '2017-06-27 10:01:07', 'incontriamoci')
        testExtract_it('incontriamoci tra 1 ora',
                       '2017-06-27 11:01:02', 'incontriamoci')
        testExtract_it('incontriamoci tra 2 ore',
                       '2017-06-27 12:01:02', 'incontriamoci')
        testExtract_it('incontriamoci tra 1 minuto',
                       '2017-06-27 10:02:02', 'incontriamoci')
        testExtract_it('incontriamoci tra 1 secondo',
                       '2017-06-27 10:01:03', 'incontriamoci')

    def test_spaces_it(self):
        """
        Test cases for Italian remove spaces
        """
        self.assertEqual(normalize('questo   è    un    test  ',
                                   lang='it'), 'questo è 1 test')
        self.assertEqual(normalize('un  altro test  ',
                                   lang='it'), '1 altro test')
        self.assertEqual(normalize('questa è un\'  altra amica   ', lang='it',
                                   remove_articles=False),
                         'questa è 1 altra amica')
        self.assertEqual(normalize('questo   è  un    test   ', lang='it',
                                   remove_articles=False), 'questo è 1 test')

    def test_numbers_it(self):
        """
        Test cases for Italian normalize lang='it'
        """
        self.assertEqual(normalize('è un test sette otto nove',
                                   lang='it'), 'è 1 test 7 8 9')
        self.assertEqual(normalize('test zero dieci undici dodici tredici',
                                   lang='it'), 'test 0 10 11 12 13')
        self.assertEqual(normalize('test mille seicento sessanta e sei',
                                   lang='it', remove_articles=False),
                         'test 1000 600 60 e 6')
        self.assertEqual(normalize('test sette e mezzo',
                                   lang='it', remove_articles=False),
                         'test 7 e 0.5')
        self.assertEqual(normalize('test due punto nove',
                                   lang='it'), 'test 2 punto 9')
        self.assertEqual(normalize('test cento e nove',
                                   lang='it', remove_articles=False),
                         'test 100 e 9')
        self.assertEqual(normalize('test venti e 1',
                                   lang='it'), 'test 20 e 1')
        self.assertEqual(normalize('test ventuno e ventisette',
                                   lang='it'), 'test 21 e 27')

    def test_multiple_numbers_it(self):
        self.assertEqual(extract_numbers('questo è il test uno due tre',
                                         lang='it'), [1.0, 2.0, 3.0])
        self.assertEqual(extract_numbers('questo è il test quattro sette' +
                                         ' quattro',
                                         lang='it'), [4.0, 7.0, 4.0])
        self.assertEqual(extract_numbers('questo  è il test cinque sei sette',
                                         lang='it'), [5.0, 6.0, 7.0])
        self.assertEqual(extract_numbers('questo è  test dieci undici dodici',
                                         lang='it'), [10.0, 11.0, 12.0])
        self.assertEqual(extract_numbers('test dodici gatti ventuno',
                                         lang='it'), [21.0, 12.0])
        self.assertEqual(extract_numbers('1 cane, sette maiali, macdonald ' +
                                         'aveva la fattoria, 3 volte' +
                                         ' 5 macarena',
                                         lang='it'), [1, 7, 3, 5])
        self.assertEqual(extract_numbers('due birre per due orsi',
                                         lang='it'), [2.0, 2.0])
        self.assertEqual(extract_numbers('venti quaranta trenta',
                                         lang='it'), [20, 40, 30])
        self.assertEqual(extract_numbers('venti 20 22',
                                         lang='it'), [20, 20, 22])
        self.assertEqual(extract_numbers('ventidue matti venti ratti '
                                         'venti gatti',
                                         lang='it'), [22, 20, 20])
        self.assertEqual(extract_numbers('venti 20 venti 2',
                                         lang='it'), [20, 20, 20, 2])
        self.assertEqual(extract_numbers('un terzo uno',
                                         lang='it'), [1 / 3, 1])
        # self.assertEqual(extract_numbers('un terzo uno',
        #                       lang='it', ordinals=True), [3])
        self.assertEqual(extract_numbers('sei miliardi', lang='it',
                                         short_scale=True), [6e9])
        self.assertEqual(extract_numbers('seimilioni', lang='it',
                                         short_scale=False), [6e6])
        self.assertEqual(extract_numbers('dodici maiali accompagnano \
         seimiliardi di batteri', lang='it', short_scale=True), [6e9, 12])

        # TODO case when pronounced/extracted number don't match
        # fractional numbers often fail
        # self.assertEqual(extract_numbers('questo è un sette otto\
        #                  nove e mezzo test',lang='it'), [7.0, 8.0, 9.5])
        # TODO pronounce number should accept short_scale flag
        # self.assertEqual(extract_numbers('two pigs and six trillion
        # bacteria', short_scale=False), [2, 6e18])
        # TODO pronounce_number should accept ordinals flag
        # self.assertEqual(extract_numbers('thirty second or first',
        #                                 ordinals=True), [32, 1])

    def test_extractdatetime_default_it(self):
        default = time(9, 0, 0)
        anchor = datetime(2017, 6, 27, 0, 0)
        res = extract_datetime('Come è il meteo 3 tra giorni?',
                               anchor, lang='it-it', default_time=default)
        self.assertEqual(default, res[0].time())

    def test_gender_it(self):
        """
        Test cases for Italian grammar , lang='it'
        """
        self.assertEqual(get_gender('mucca', lang='it'), 'f')
        self.assertEqual(get_gender('cavallo', lang='it'), 'm')
        self.assertEqual(get_gender('mucche', 'le mucche', lang='it'), 'f')
        self.assertEqual(get_gender('bue', 'il bue mangia la erba',
                                    lang='it'), 'm')
        self.assertEqual(get_gender('pesce', 'il pesce nuota',
                                    lang='it'), 'm')
        self.assertEqual(get_gender('tigre', lang='it'), 'f')
        self.assertEqual(get_gender('uomini', 'questi uomini mangiano pasta',
                                    lang='it'), 'm')
        self.assertEqual(get_gender('ponte', 'il ponte', lang='it'), 'm')
        self.assertEqual(get_gender('ponte', u'questo ponte è caduto',
                                    lang='it'), 'm')
        self.assertEqual(get_gender('scultrice', 'questa scultrice famosa',
                                    lang='it'), 'f')
        self.assertEqual(get_gender('scultore', 'questo scultore famoso',
                                    lang='it'), 'm')
        self.assertEqual(get_gender('scultori', 'gli scultori rinascimentali',
                                    lang='it'), 'm')
        self.assertEqual(get_gender('scultrici', 'le scultrici moderne',
                                    lang='it'), 'f')


if __name__ == '__main__':
    unittest.main()
