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

from mycroft.util.parse import normalize, extract_numbers, extract_number, \
    extract_datetime, extract_datetime_es, isFractional_es


class TestNormalize_es(unittest.TestCase):
    """
        Test cases for Spanish parsing
    """

    def test_articles_es(self):
        self.assertEqual(normalize("esta es la prueba", lang="es",
                                   remove_articles=True),
                         "esta es prueba")
        self.assertEqual(normalize("y otra prueba", lang="es",
                                   remove_articles=True),
                         "y otra prueba")

    def test_numbers_es(self):
        self.assertEqual(normalize("esto es un uno una", lang="es"),
                         "esto es 1 1 1")
        self.assertEqual(normalize("esto es dos tres prueba", lang="es"),
                         "esto es 2 3 prueba")
        self.assertEqual(normalize("esto es cuatro cinco seis prueba",
                                   lang="es"),
                         "esto es 4 5 6 prueba")
        self.assertEqual(normalize(u"siete mï¿½s ocho mï¿½s nueve", lang="es"),
                         u"7 mï¿½s 8 mï¿½s 9")
        self.assertEqual(normalize("diez once doce trece catorce quince",
                                   lang="es"),
                         "10 11 12 13 14 15")
        self.assertEqual(normalize(u"dieciséis diecisiete", lang="es"),
                         "16 17")
        self.assertEqual(normalize(u"dieciocho diecinueve", lang="es"),
                         "18 19")
        self.assertEqual(normalize(u"veinte treinta cuarenta", lang="es"),
                         "20 30 40")
        self.assertEqual(normalize(u"treinta y dos caballos", lang="es"),
                         "32 caballos")
        self.assertEqual(normalize(u"cien caballos", lang="es"),
                         "100 caballos")
        self.assertEqual(normalize(u"ciento once caballos", lang="es"),
                         "111 caballos")
        self.assertEqual(normalize(u"habï¿½a cuatrocientas una vacas",
                                   lang="es"),
                         u"habï¿½a 401 vacas")
        self.assertEqual(normalize(u"dos mil", lang="es"),
                         "2000")
        self.assertEqual(normalize(u"dos mil trescientas cuarenta y cinco",
                                   lang="es"),
                         "2345")
        self.assertEqual(normalize(
            u"ciento veintitrés mil cuatrocientas cincuenta y seis",
            lang="es"),
            "123456")
        self.assertEqual(normalize(
            u"quinientas veinticinco mil", lang="es"),
            "525000")
        self.assertEqual(normalize(
            u"novecientos noventa y nueve mil novecientos noventa y nueve",
            lang="es"),
            "999999")

    def test_extract_number_es(self):
        self.assertEqual(sorted(extract_numbers(
            "1 7 cuatro catorce ocho 157", lang='es')), [1, 4, 7, 8, 14, 157])
        self.assertEqual(sorted(extract_numbers(
            "1 7 cuatro albuquerque naranja John Doe catorce ocho 157",
            lang='es')), [1, 4, 7, 8, 14, 157])
        self.assertEqual(extract_number("seis punto dos", lang='es'), 6.2)
        self.assertEqual(extract_numbers("un medio", lang='es'), [0.5])
        self.assertEqual(extract_number("cuarto", lang='es'), 0.25)

        self.assertEqual(extract_number("2.0", lang='es'), 2.0)
        self.assertEqual(extract_number("1/4", lang='es'), 0.25)

        self.assertEqual(extract_number("dos e media", lang='es'), 2.5)
        self.assertEqual(extract_number(
            "catorce e milésima", lang='es'), 14.001)

        self.assertEqual(extract_number("dos punto cero dos", lang='es'), 2.02)

    def test_isFraction_es(self):
        self.assertEqual(isFractional_es("vigésimo"), 1.0 / 20)
        self.assertEqual(isFractional_es("trigésimo"), 1.0 / 30)
        self.assertEqual(isFractional_es("centésima"), 1.0 / 100)
        self.assertEqual(isFractional_es("milésima"), 1.0 / 1000)


class TestDatetime_es(unittest.TestCase):

    def test_datetime_by_date_es(self):
        # test currentDate==None
        _now = datetime(year=2019, month=10, day=10)
        relative_year = _now.year if _now.day == 1 else (_now.year + 1)
        self.assertEqual(extract_datetime_es("11 ene")[0],
                         datetime(relative_year, 1, 11))

        # test months

        self.assertEqual(extract_datetime(
            "11 ene", lang='es', anchorDate=datetime(1998, 1, 1))[0],
            datetime(1998, 1, 11))
        self.assertEqual(extract_datetime(
            "11 feb", lang='es', anchorDate=datetime(1998, 2, 1))[0],
            datetime(1998, 2, 11))
        self.assertEqual(extract_datetime(
            "11 mar", lang='es', anchorDate=datetime(1998, 3, 1))[0],
            datetime(1998, 3, 11))
        self.assertEqual(extract_datetime(
            "11 abr", lang='es', anchorDate=datetime(1998, 4, 1))[0],
            datetime(1998, 4, 11))
        self.assertEqual(extract_datetime(
            "11 may", lang='es', anchorDate=datetime(1998, 5, 1))[0],
            datetime(1998, 5, 11))
        # there is an issue with the months of june through september (below)
        # hay un problema con las meses junio hasta septiembre (lea abajo)
        self.assertEqual(extract_datetime(
            "11 oct", lang='es', anchorDate=datetime(1998, 10, 1))[0],
            datetime(1998, 10, 11))
        self.assertEqual(extract_datetime(
            "11 nov", lang='es', anchorDate=datetime(1998, 11, 1))[0],
            datetime(1998, 11, 11))
        self.assertEqual(extract_datetime(
            "11 dic", lang='es', anchorDate=datetime(1998, 12, 1))[0],
            datetime(1998, 12, 11))

        self.assertEqual(extract_datetime("", lang='es'), None)

    # TODO fix bug causing these tests to fail (MycroftAI/mycroft-core#2348)
    #         reparar error de traducción preveniendo las funciones abajo de
    #         retornar correctamente
    #         (escribido con disculpas por un Inglés hablante)
    #      further broken tests are below their respective working tests.
    @unittest.skip("currently processing these months incorrectly")
    def test_bugged_output_wastebasket(self):
        self.assertEqual(extract_datetime(
            "11 jun", lang='es', anchorDate=datetime(1998, 6, 1))[0],
            datetime(1998, 6, 11))
        self.assertEqual(extract_datetime(
            "11 junio", lang='es', anchorDate=datetime(1998, 6, 1))[0],
            datetime(1998, 6, 11))
        self.assertEqual(extract_datetime(
            "11 jul", lang='es', anchorDate=datetime(1998, 7, 1))[0],
            datetime(1998, 7, 11))
        self.assertEqual(extract_datetime(
            "11 ago", lang='es', anchorDate=datetime(1998, 8, 1))[0],
            datetime(1998, 8, 11))
        self.assertEqual(extract_datetime(
            "11 sep", lang='es', anchorDate=datetime(1998, 9, 1))[0],
            datetime(1998, 9, 11))

        # It's also failing on years
        self.assertEqual(extract_datetime(
            "11 ago 1998", lang='es')[0], datetime(1998, 8, 11))

    def test_extract_datetime_relative(self):
        self.assertEqual(extract_datetime("esta noche", anchorDate=datetime(
            1998, 1, 1), lang='es'),
            [datetime(1998, 1, 1, 21, 0, 0), 'esta'])
        self.assertEqual(extract_datetime(
            "ayer noche", anchorDate=datetime(1998, 1, 1),
            lang='es')[0], datetime(1997, 12, 31, 21))
        self.assertEqual(extract_datetime(
            "el noche anteayer", anchorDate=datetime(1998, 1, 1),
            lang='es')[0], datetime(1997, 12, 30, 21))
        self.assertEqual(extract_datetime(
            "el noche ante ante ayer", anchorDate=datetime(1998, 1, 1),
            lang='es')[0], datetime(1997, 12, 29, 21))
        self.assertEqual(extract_datetime(
            "mañana en la mañana", anchorDate=datetime(1998, 1, 1),
            lang='es')[0], datetime(1998, 1, 2, 8))
        self.assertEqual(extract_datetime(
            "ayer en la tarde", anchorDate=datetime(1998, 1, 1),
            lang='es')[0], datetime(1997, 12, 31, 15))

        self.assertEqual(extract_datetime(
            "que año es", anchorDate=datetime(1998, 1, 1),
            lang='es')[0], datetime(1998, 1, 1))

        self.assertEqual(extract_datetime("hoy 2 a.m.", lang='es',
                                          anchorDate=datetime(1998, 1, 1))[0],
                         datetime(1998, 1, 1, 2))
        self.assertEqual(extract_datetime("hoy 2 am", lang='es',
                                          anchorDate=datetime(1998, 1, 1))[0],
                         datetime(1998, 1, 1, 2))
        self.assertEqual(extract_datetime("hoy 2 p.m.", lang='es',
                                          anchorDate=datetime(1998, 1, 1))[0],
                         datetime(1998, 1, 1, 14))
        self.assertEqual(extract_datetime("hoy 2 pm", lang='es',
                                          anchorDate=datetime(1998, 1, 1))[0],
                         datetime(1998, 1, 1, 14))

    @unittest.skip("These phrases are not parsing correctly.")
    # parses as "morning" and returns 8:00 on anchorDate
    def test_extract_datetime_relative_failing(self):
        self.assertEqual(extract_datetime(
            "mañana", anchorDate=datetime(1998, 1, 1), lang='es')[0],
            datetime(1998, 1, 2))


if __name__ == "__main__":
    unittest.main()
