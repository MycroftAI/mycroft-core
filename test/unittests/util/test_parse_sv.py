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
    def test_extractnumber_sv(self):
        self.assertEqual(extractnumber("1 och en halv deciliter",
                                       lang='sv-se'), 1.5)
        self.assertEqual(extractnumber("det här är det första testet",
                                       lang='sv-se'), 1)
        self.assertEqual(extractnumber("det här är test nummer 2",
                                       lang='sv-se'), 2)
        self.assertEqual(extractnumber("det här är det andra testet",
                                       lang='sv-se'), 2)
        self.assertEqual(extractnumber("det här är tredje testet",
                                       lang='sv-se'), 3)
        self.assertEqual(extractnumber("det här är test nummer 4",
                                       lang='sv-se'), 4)
        self.assertEqual(extractnumber("en tredjedels dl",
                                       lang='sv-se'), 1.0 / 3.0)
        self.assertEqual(extractnumber("tre deciliter",
                                       lang='sv-se'), 3)
        self.assertEqual(extractnumber("1/3 deciliter",
                                       lang='sv-se'), 1.0 / 3.0)
        self.assertEqual(extractnumber("en kvarts dl",
                                       lang='sv-se'), 0.25)
        self.assertEqual(extractnumber("1/4 dl",
                                       lang='sv-se'), 0.25)
        self.assertEqual(extractnumber("en kvarts dl",
                                       lang='sv-se'), 0.25)
        self.assertEqual(extractnumber("2/3 dl",
                                       lang='sv-se'), 2.0 / 3.0)
        self.assertEqual(extractnumber("3/4 dl",
                                       lang='sv-se'), 3.0 / 4.0)
        self.assertEqual(extractnumber("1 och 3/4 dl",
                                       lang='sv-se'), 1.75)
        self.assertEqual(extractnumber("tre fjärdedels dl",
                                       lang='sv-se'), 3.0 / 4.0)
        self.assertEqual(extractnumber("trekvarts kopp",
                                       lang='sv-se'), 3.0 / 4.0)

    def test_extractdatetime_sv(self):
        def extractWithFormat(text):
            date = datetime(2017, 6, 27, 0, 0)
            [extractedDate, leftover] = extract_datetime(text, date,
                                                         lang='sv-se')
            extractedDate = extractedDate.strftime("%Y-%m-%d %H:%M:%S")
            return [extractedDate, leftover]

        def testExtract(text, expected_date, expected_leftover):
            res = extractWithFormat(text)
            self.assertEqual(res[0], expected_date)
            self.assertEqual(res[1], expected_leftover)

        testExtract("Planera bakhållet 5 dagar från nu",
                    "2017-07-02 00:00:00", "planera bakhållet")
        testExtract("Vad blir vädret i övermorgon?",
                    "2017-06-29 00:00:00", "vad blir vädret")
        testExtract("Påminn mig klockan 10:45",
                    "2017-06-27 10:45:00", "påminn mig klockan")
        testExtract("vad blir vädret på fredag morgon",
                    "2017-06-30 08:00:00", "vad blir vädret")
        testExtract("vad blir morgondagens väder",
                    "2017-06-28 00:00:00", "vad blir väder")
        testExtract("påminn mig att ringa mamma om 8 veckor och 2 dagar",
                    "2017-08-24 00:00:00", "påminn mig att ringa mamma om och")
        testExtract("Spela Kurt Olssons musik 2 dagar från Fredag",
                    "2017-07-02 00:00:00", "spela kurt olssons musik")
        testExtract("vi möts 20:00",
                    "2017-06-27 20:00:00", "vi möts")

    def test_numbers(self):
        self.assertEqual(normalize("det här är ett ett två tre  test",
                                   lang='sv-se'),
                         "det här är 1 1 2 3 test")
        self.assertEqual(normalize("  det är fyra fem sex  test",
                                   lang='sv-se'),
                         "det är 4 5 6 test")
        self.assertEqual(normalize("det är sju åtta nio test",
                                   lang='sv-se'),
                         "det är 7 8 9 test")
        self.assertEqual(normalize("det är tio elva tolv test",
                                   lang='sv-se'),
                         "det är 10 11 12 test")
        self.assertEqual(normalize("det är arton nitton tjugo test",
                                   lang='sv-se'),
                         "det är 18 19 20 test")


if __name__ == "__main__":
    unittest.main()
