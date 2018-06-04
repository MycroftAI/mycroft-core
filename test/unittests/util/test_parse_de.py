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

from mycroft.util.parse import get_gender
from mycroft.util.parse import extract_datetime
from mycroft.util.parse import extractnumber
from mycroft.util.parse import normalize
from mycroft.util.parse import fuzzy_match
from mycroft.util.parse import match_one





class TestNormalize(unittest.TestCase):
    def test_articles(self):
        self.assertEqual(normalize("dies ist der test", lang="de-de", remove_articles=True),
                         "dies ist test")
        self.assertEqual(normalize("und noch ein Test", lang="de-de", remove_articles=True),
                         "und noch 1 Test")
        self.assertEqual(normalize("dies ist der Extra-Test", lang="de-de",
                                   remove_articles=False),
                         "dies ist der Extra-Test")

    def test_extractnumber(self):
        self.assertEqual(extractnumber("dies ist der erste Test"), 1)
        self.assertEqual(extractnumber("dies ist 2 Test"), 2)
        self.assertEqual(extractnumber("dies ist zweiter Test"), 2)
        self.assertEqual(extractnumber("dies ist der dritte Test"), 3)
        self.assertEqual(extractnumber("dies ist der Test Nummer 4"), 4)
        self.assertEqual(extractnumber("ein drittel einer Tasse"), 1.0 / 3.0)
        self.assertEqual(extractnumber("drei Tassen"), 3)
        self.assertEqual(extractnumber("1/3 Tasse"), 1.0 / 3.0)
        self.assertEqual(extractnumber("eine viertel Tasse"), 0.25)
        self.assertEqual(extractnumber("1/4 Tasse"), 0.25)
        self.assertEqual(extractnumber("viertel Tasse"), 0.25)
        self.assertEqual(extractnumber("2/3 Tasse"), 2.0 / 3.0)
        self.assertEqual(extractnumber("3/4 Tasse"), 3.0 / 4.0)
        self.assertEqual(extractnumber("1 und 3/4 Tassen"), 1.75)
        self.assertEqual(extractnumber("1 Tasse und eine halbe"), 1.5)
        self.assertEqual(extractnumber("eine Tasse und eine halbe"), 1.5)
        self.assertEqual(extractnumber("eine und eine halbe Tasse"), 1.5)
        self.assertEqual(extractnumber("ein und ein halb Tassen"), 1.5)
        self.assertEqual(extractnumber("drei Viertel Tasse"), 3.0 / 4.0)
        self.assertEqual(extractnumber("drei Viertel Tassen"), 3.0 / 4.0)

    def test_extractdatetime_de(self):
        def extractWithFormat(text):
            date = datetime(2017, 6, 27, 0, 0)
            [extractedDate, leftover] = extract_datetime(text, date, lang="de-de",)
            extractedDate = extractedDate.strftime("%Y-%m-%d %H:%M:%S")
            return [extractedDate, leftover]

        def testExtract(text, expected_date, expected_leftover):
            res = extractWithFormat(text)
            self.assertEqual(res[0], expected_date)
            self.assertEqual(res[1], expected_leftover)

       # testExtract(u"setze den frisörtermin auf 5 tage von heute",
       #             "2017-07-02 00:00:00", u"setze frisörtermin")
       # testExtract(u"wie ist das wetter übermorgen?",
       #             "2017-06-29 00:00:00", "wie ist das wetter")
       # testExtract("erinnere mich um 10:45 abends",
       #             "2017-06-27 22:45:00", "erinnere mich")
       # testExtract("was ist das Wetter am freitag morgen",
       #             "2017-06-30 08:00:00", "was ist das wetter")
       # testExtract("wie ist das wetter morgen",
       #             "2017-06-28 00:00:00", "wie ist das wetter")
       # testExtract("erinnere mich meine mutter anzurufen in 8 Wochen und 2 Tagen",
       #             "2017-08-24 00:00:00", "erinnere mich meine mutter anzurufen")
       # testExtract("spiele rick astley musik 2 tage von freitag",
       #             "2017-07-02 00:00:00", "spiele rick astley musik")
       # testExtract("starte die invasion um 3:45 pm am Donnerstag",
       #             "2017-06-29 15:45:00", "starte die invasion")
       # testExtract(u"am montag bestelle kuchen von der bäckerei",
       #             "2017-07-03 00:00:00", u"bestelle kuchen von bäckerei")
       # testExtract("spiele happy birthday musik 5 jahre von heute",
       #             "2022-06-27 00:00:00", "spiele happy birthday musik")
       # testExtract(u"skype mama um 12:45 pm nächsten Donnerstag",
       #             "2017-07-06 12:45:00", "skype mama")
       # testExtract(u"wie ist das wetter nächsten donnerstag?",
       #             "2017-07-06 00:00:00", "wie ist das wetter")
       # testExtract(u"wie ist das Wetter nächsten Freitag morgen",
       #             "2017-07-07 08:00:00", "wie ist das wetter")
       # testExtract(u"wie ist das wetter nächsten freitag abend",
       #             "2017-07-07 19:00:00", "wie ist das wetter")
       # testExtract("wie ist das wetter nächsten freitag nachmittag",
       #             "2017-07-07 15:00:00", "wie ist das wetter")
       # testExtract(u"erinnere mich mama anzurufen am dritten august",
       #             "2017-08-03 00:00:00", "erinnere mich mama anzurufen")
       # testExtract("kaufe feuerwerk am einundzwanzigsten juli",
       #             "2017-07-21 00:00:00", "kaufe feuerwerk")
        testExtract(u"wie ist das wetter 2 wochen ab nächsten freitag",
                    "2017-07-21 00:00:00", "wie ist das wetter")
        testExtract("wie ist das wetter am mittwoch um 07:00",
                    "2017-06-28 07:00:00", "wie ist das wetter")
        testExtract("wie ist das wetter am mittwoch um 7 uhr",
                    "2017-06-28 07:00:00", "wie ist das wetter")
        testExtract("Mache einen Termin um 12:45 pm nächsten donnerstag",
                    "2017-07-06 12:45:00", "mache einen termin")
        testExtract("wie ist das wetter an diesem donnerstag?",
                    "2017-06-29 00:00:00", "wie wetter")
        testExtract("vereinbare den besuch für 2 wochen und 6 tage ab sonntag",
                    "2017-07-21 00:00:00", "vereinbare besuch")
        testExtract("beginne die invasion um 03 45 am donnerstag",
                    "2017-06-29 03:45:00", "beginne invasion")
        testExtract("beginne die invasion um 8 Uhr am donnerstag",
                    "2017-06-29 08:00:00", "beginne invasion")
        testExtract("starte die party um 8 uhr abends am donnerstag",
                    "2017-06-29 20:00:00", "starte party")
        testExtract("starte die invasion um 8 abends am donnerstag",
                    "2017-06-29 20:00:00", "starte invasion")
        testExtract("starte die invasion am donnerstag um mittag",
                    "2017-06-29 12:00:00", "starte invasion")
        testExtract("starte die invasion am donnerstag um mitternacht",
                    "2017-06-29 00:00:00", "starte invasion")
        testExtract("starte die invasion am donnerstag um 5 uhr",
                    "2017-06-29 05:00:00", "starte invasion")
        testExtract("erinnere mich uafzuwachen in 4 jahren",
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
        self.assertEqual(normalize("  dies   ist  ein    test"),
                         "dies  ist Test")
        self.assertEqual(normalize("  dies   ist  ein    test  "),
                         "dies ist test")


    def test_numbers(self):
        self.assertEqual(normalize("dies ist eins zwei drei test"),
                         "dies ist 1 2 3 test")
        self.assertEqual(normalize(u"es ist vier fünf sechs test"),
                         "es ist  4 5 6 test")
        self.assertEqual(normalize("es ist sieben acht neun test"),
                         "es ist 7 8 9 test")
        self.assertEqual(normalize("es ist sieben acht neun test"),
                         "es ist 7 8 9 test")
        self.assertEqual(normalize(u"das ist zehn elf zwölf test"),
                         "das ist 10 11 12 test")
        self.assertEqual(normalize("das ist ein dreizehn vierzehn test"),
                         "das ist 13 14 test")
        self.assertEqual(normalize(u"das ist fünfzehn sechszehn siebzehn"),
                         "das ist 15 16 17")
        self.assertEqual(normalize("das ist achtzehn neunzehn zwanzig"),
                         "das ist 18 19 20")
'''
    def test_contractions(self):
        self.assertEqual(normalize("ain't"), "is not")
        self.assertEqual(normalize("aren't"), "are not")
        self.assertEqual(normalize("can't"), "can not")
        self.assertEqual(normalize("could've"), "could have")
        self.assertEqual(normalize("couldn't"), "could not")
        self.assertEqual(normalize("didn't"), "did not")
        self.assertEqual(normalize("doesn't"), "does not")
        self.assertEqual(normalize("don't"), "do not")
        self.assertEqual(normalize("gonna"), "going to")
        self.assertEqual(normalize("gotta"), "got to")
        self.assertEqual(normalize("hadn't"), "had not")
        self.assertEqual(normalize("hadn't have"), "had not have")
        self.assertEqual(normalize("hasn't"), "has not")
        self.assertEqual(normalize("haven't"), "have not")
        # TODO: Ambiguous with "he had"
        self.assertEqual(normalize("he'd"), "he would")
        self.assertEqual(normalize("he'll"), "he will")
        # TODO: Ambiguous with "he has"
        self.assertEqual(normalize("he's"), "he is")
        # TODO: Ambiguous with "how would"
        self.assertEqual(normalize("how'd"), "how did")
        self.assertEqual(normalize("how'll"), "how will")
        # TODO: Ambiguous with "how has" and "how does"
        self.assertEqual(normalize("how's"), "how is")
        # TODO: Ambiguous with "I had"
        self.assertEqual(normalize("I'd"), "I would")
        self.assertEqual(normalize("I'll"), "I will")
        self.assertEqual(normalize("I'm"), "I am")
        self.assertEqual(normalize("I've"), "I have")
        self.assertEqual(normalize("I haven't"), "I have not")
        self.assertEqual(normalize("isn't"), "is not")
        self.assertEqual(normalize("it'd"), "it would")
        self.assertEqual(normalize("it'll"), "it will")
        # TODO: Ambiguous with "it has"
        self.assertEqual(normalize("it's"), "it is")
        self.assertEqual(normalize("it isn't"), "it is not")
        self.assertEqual(normalize("mightn't"), "might not")
        self.assertEqual(normalize("might've"), "might have")
        self.assertEqual(normalize("mustn't"), "must not")
        self.assertEqual(normalize("mustn't have"), "must not have")
        self.assertEqual(normalize("must've"), "must have")
        self.assertEqual(normalize("needn't"), "need not")
        self.assertEqual(normalize("oughtn't"), "ought not")
        self.assertEqual(normalize("shan't"), "shall not")
        # TODO: Ambiguous wiht "she had"
        self.assertEqual(normalize("she'd"), "she would")
        self.assertEqual(normalize("she hadn't"), "she had not")
        self.assertEqual(normalize("she'll"), "she will")
        self.assertEqual(normalize("she's"), "she is")
        self.assertEqual(normalize("she isn't"), "she is not")
        self.assertEqual(normalize("should've"), "should have")
        self.assertEqual(normalize("shouldn't"), "should not")
        self.assertEqual(normalize("shouldn't have"), "should not have")
        self.assertEqual(normalize("somebody's"), "somebody is")
        # TODO: Ambiguous with "someone had"
        self.assertEqual(normalize("someone'd"), "someone would")
        self.assertEqual(normalize("someone hadn't"), "someone had not")
        self.assertEqual(normalize("someone'll"), "someone will")
        # TODO: Ambiguous with "someone has"
        self.assertEqual(normalize("someone's"), "someone is")
        self.assertEqual(normalize("that'll"), "that will")
        # TODO: Ambiguous with "that has"
        self.assertEqual(normalize("that's"), "that is")
        # TODO: Ambiguous with "that had"
        self.assertEqual(normalize("that'd"), "that would")
        # TODO: Ambiguous with "there had"
        self.assertEqual(normalize("there'd"), "there would")
        self.assertEqual(normalize("there're"), "there are")
        # TODO: Ambiguous with "there has"
        self.assertEqual(normalize("there's"), "there is")
        # TODO: Ambiguous with "they had"
        self.assertEqual(normalize("they'd"), "they would")
        self.assertEqual(normalize("they'll"), "they will")
        self.assertEqual(normalize("they won't have"), "they will not have")
        self.assertEqual(normalize("they're"), "they are")
        self.assertEqual(normalize("they've"), "they have")
        self.assertEqual(normalize("they haven't"), "they have not")
        self.assertEqual(normalize("wasn't"), "was not")
        # TODO: Ambiguous wiht "we had"
        self.assertEqual(normalize("we'd"), "we would")
        self.assertEqual(normalize("we would've"), "we would have")
        self.assertEqual(normalize("we wouldn't"), "we would not")
        self.assertEqual(normalize("we wouldn't have"), "we would not have")
        self.assertEqual(normalize("we'll"), "we will")
        self.assertEqual(normalize("we won't have"), "we will not have")
        self.assertEqual(normalize("we're"), "we are")
        self.assertEqual(normalize("we've"), "we have")
        self.assertEqual(normalize("weren't"), "were not")
        self.assertEqual(normalize("what'd"), "what did")
        self.assertEqual(normalize("what'll"), "what will")
        self.assertEqual(normalize("what're"), "what are")
        # TODO: Ambiguous with "what has" / "what does")
        self.assertEqual(normalize("whats"), "what is")
        self.assertEqual(normalize("what's"), "what is")
        self.assertEqual(normalize("what've"), "what have")
        # TODO: Ambiguous with "when has"
        self.assertEqual(normalize("when's"), "when is")
        self.assertEqual(normalize("where'd"), "where did")
        # TODO: Ambiguous with "where has" / where does"
        self.assertEqual(normalize("where's"), "where is")
        self.assertEqual(normalize("where've"), "where have")
        # TODO: Ambiguous with "who had" "who did")
        self.assertEqual(normalize("who'd"), "who would")
        self.assertEqual(normalize("who'd've"), "who would have")
        self.assertEqual(normalize("who'll"), "who will")
        self.assertEqual(normalize("who're"), "who are")
        # TODO: Ambiguous with "who has" / "who does"
        self.assertEqual(normalize("who's"), "who is")
        self.assertEqual(normalize("who've"), "who have")
        self.assertEqual(normalize("why'd"), "why did")
        self.assertEqual(normalize("why're"), "why are")
        # TODO: Ambiguous with "why has" / "why does"
        self.assertEqual(normalize("why's"), "why is")
        self.assertEqual(normalize("won't"), "will not")
        self.assertEqual(normalize("won't've"), "will not have")
        self.assertEqual(normalize("would've"), "would have")
        self.assertEqual(normalize("wouldn't"), "would not")
        self.assertEqual(normalize("wouldn't've"), "would not have")
        self.assertEqual(normalize("ya'll"), "you all")
        self.assertEqual(normalize("y'all"), "you all")
        self.assertEqual(normalize("y'ain't"), "you are not")
        # TODO: Ambiguous with "you had"
        self.assertEqual(normalize("you'd"), "you would")
        self.assertEqual(normalize("you'd've"), "you would have")
        self.assertEqual(normalize("you'll"), "you will")
        self.assertEqual(normalize("you're"), "you are")
        self.assertEqual(normalize("you aren't"), "you are not")
        self.assertEqual(normalize("you've"), "you have")
        self.assertEqual(normalize("you haven't"), "you have not")

    def test_combinations(self):
        self.assertEqual(normalize("I couldn't have guessed there'd be two"),
                         "I could not have guessed there would be 2")
        self.assertEqual(normalize("I wouldn't have"), "I would not have")
        self.assertEqual(normalize("I hadn't been there"),
                         "I had not been there")
        self.assertEqual(normalize("I would've"), "I would have")
        self.assertEqual(normalize("it hadn't"), "it had not")
        self.assertEqual(normalize("it hadn't have"), "it had not have")
        self.assertEqual(normalize("it would've"), "it would have")
        self.assertEqual(normalize("she wouldn't have"), "she would not have")
        self.assertEqual(normalize("she would've"), "she would have")
        self.assertEqual(normalize("someone wouldn't have"),
                         "someone would not have")
        self.assertEqual(normalize("someone would've"), "someone would have")
        self.assertEqual(normalize("what's the weather like"),
                         "what is weather like")
        self.assertEqual(normalize("that's what I told you"),
                         "that is what I told you")

        self.assertEqual(normalize("whats 8 + 4"), "what is 8 + 4")

    def test_gender(self):
        self.assertEqual(get_gender("person"),
                         False)
'''

if __name__ == "__main__":
    unittest.main()
