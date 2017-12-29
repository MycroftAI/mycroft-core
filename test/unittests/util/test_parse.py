# -*- coding: iso-8859-15 -*-
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


class TestFuzzyMatch(unittest.TestCase):
    def test_matches(self):
        self.assertTrue(fuzzy_match("you and me", "you and me") >= 1.0)
        self.assertTrue(fuzzy_match("you and me", "you") < 0.5)
        self.assertTrue(fuzzy_match("You", "you") > 0.5)
        self.assertTrue(fuzzy_match("you and me", "you") ==
                        fuzzy_match("you", "you and me"))
        self.assertTrue(fuzzy_match("you and me", "he or they") < 0.2)


class TestNormalize(unittest.TestCase):
    def test_articles(self):
        self.assertEqual(normalize("this is a test", remove_articles=True),
                         "this is test")
        self.assertEqual(normalize("this is the test", remove_articles=True),
                         "this is test")
        self.assertEqual(normalize("and another test", remove_articles=True),
                         "and another test")
        self.assertEqual(normalize("this is an extra test",
                                   remove_articles=False),
                         "this is an extra test")

    def test_extractnumber(self):
        self.assertEqual(extractnumber("this is the first test"), 1)
        self.assertEqual(extractnumber("this is 2 test"), 2)
        self.assertEqual(extractnumber("this is second test"), 2)
        self.assertEqual(extractnumber("this is the third test"), 1.0 / 3.0)
        self.assertEqual(extractnumber("this is test number 4"), 4)
        self.assertEqual(extractnumber("one third of a cup"), 1.0 / 3.0)
        self.assertEqual(extractnumber("three cups"), 3)
        self.assertEqual(extractnumber("1/3 cups"), 1.0 / 3.0)
        self.assertEqual(extractnumber("quarter cup"), 0.25)
        self.assertEqual(extractnumber("1/4 cup"), 0.25)
        self.assertEqual(extractnumber("one fourth cup"), 0.25)
        self.assertEqual(extractnumber("2/3 cups"), 2.0 / 3.0)
        self.assertEqual(extractnumber("3/4 cups"), 3.0 / 4.0)
        self.assertEqual(extractnumber("1 and 3/4 cups"), 1.75)
        self.assertEqual(extractnumber("1 cup and a half"), 1.5)
        self.assertEqual(extractnumber("one cup and a half"), 1.5)
        self.assertEqual(extractnumber("one and a half cups"), 1.5)
        self.assertEqual(extractnumber("one and one half cups"), 1.5)
        self.assertEqual(extractnumber("three quarter cups"), 3.0 / 4.0)
        self.assertEqual(extractnumber("three quarters cups"), 3.0 / 4.0)

    def test_extractdatetime_en(self):
        def extractWithFormat(text):
            date = datetime(2017, 06, 27, 00, 00)
            [extractedDate, leftover] = extract_datetime(text, date)
            extractedDate = extractedDate.strftime("%Y-%m-%d %H:%M:%S")
            return [extractedDate, leftover]

        def testExtract(text, expected_date, expected_leftover):
            res = extractWithFormat(text)
            self.assertEqual(res[0], expected_date)
            self.assertEqual(res[1], expected_leftover)

        testExtract("Set the ambush for 5 days from today",
                    "2017-07-02 00:00:00", "set ambush")
        testExtract("What is the day after tomorrow's weather?",
                    "2017-06-29 00:00:00", "what is weather")
        testExtract("Remind me at 10:45 pm",
                    "2017-06-27 22:45:00", "remind me")
        testExtract("what is the weather on friday morning",
                    "2017-06-30 08:00:00", "what is weather")
        testExtract("what is tomorrow's weather",
                    "2017-06-28 00:00:00", "what is weather")
        testExtract("remind me to call mom in 8 weeks and 2 days",
                    "2017-08-24 00:00:00", "remind me to call mom")
        testExtract("Play Rick Astley music 2 days from Friday",
                    "2017-07-02 00:00:00", "play rick astley music")
        testExtract("Begin the invasion at 3:45 pm on Thursday",
                    "2017-06-29 15:45:00", "begin invasion")
        testExtract("On Monday, order pie from the bakery",
                    "2017-07-03 00:00:00", "order pie from bakery")
        testExtract("Play Happy Birthday music 5 years from today",
                    "2022-06-27 00:00:00", "play happy birthday music")
        testExtract("Skype Mom at 12:45 pm next Thursday",
                    "2017-07-06 12:45:00", "skype mom")
        testExtract("What's the weather next Thursday?",
                    "2017-07-06 00:00:00", "what weather")
        testExtract("what is the weather next friday morning",
                    "2017-07-07 08:00:00", "what is weather")
        testExtract("what is the weather next friday evening",
                    "2017-07-07 19:00:00", "what is weather")
        testExtract("what is the weather next friday afternoon",
                    "2017-07-07 15:00:00", "what is weather")
        testExtract("remind me to call mom on august 3rd",
                    "2017-08-03 00:00:00", "remind me to call mom")
        testExtract("Buy fireworks on the 4th of July",
                    "2017-07-04 00:00:00", "buy fireworks")
        testExtract("what is the weather 2 weeks from next friday",
                    "2017-07-21 00:00:00", "what is weather")
        testExtract("what is the weather wednesday at 0700 hours",
                    "2017-06-28 07:00:00", "what is weather")
        testExtract("what is the weather wednesday at 7 o'clock",
                    "2017-06-28 07:00:00", "what is weather")
        testExtract("Set up an appointment at 12:45 pm next Thursday",
                    "2017-07-06 12:45:00", "set up appointment")
        testExtract("What's the weather this Thursday?",
                    "2017-06-29 00:00:00", "what weather")
        testExtract("set up the visit for 2 weeks and 6 days from Saturday",
                    "2017-07-21 00:00:00", "set up visit")
        testExtract("Begin the invasion at 03 45 on Thursday",
                    "2017-06-29 03:45:00", "begin invasion")
        testExtract("Begin the invasion at o 800 hours on Thursday",
                    "2017-06-29 08:00:00", "begin invasion")
        testExtract("Begin the party at 8 o'clock in the evening on Thursday",
                    "2017-06-29 20:00:00", "begin party")
        testExtract("Begin the invasion at 8 in the evening on Thursday",
                    "2017-06-29 20:00:00", "begin invasion")
        testExtract("Begin the invasion on Thursday at noon",
                    "2017-06-29 12:00:00", "begin invasion")
        testExtract("Begin the invasion on Thursday at midnight",
                    "2017-06-29 00:00:00", "begin invasion")
        testExtract("Begin the invasion on Thursday at 0500",
                    "2017-06-29 05:00:00", "begin invasion")
        testExtract("remind me to wake up in 4 years",
                    "2021-06-27 00:00:00", "remind me to wake up")
        testExtract("remind me to wake up in 4 years and 4 days",
                    "2021-07-01 00:00:00", "remind me to wake up")
        testExtract("What is the weather 3 days after tomorrow?",
                    "2017-07-01 00:00:00", "what is weather")
        testExtract("december 3",
                    "2017-12-03 00:00:00", "")
        testExtract("lets meet at 8:00 tonight",
                    "2017-06-27 20:00:00", "lets meet")

    def test_spaces(self):
        self.assertEqual(normalize("  this   is  a    test"),
                         "this is test")
        self.assertEqual(normalize("  this   is  a    test  "),
                         "this is test")
        self.assertEqual(normalize("  this   is  one    test"),
                         "this is 1 test")

    def test_numbers(self):
        self.assertEqual(normalize("this is a one two three  test"),
                         "this is 1 2 3 test")
        self.assertEqual(normalize("  it's  a four five six  test"),
                         "it is 4 5 6 test")
        self.assertEqual(normalize("it's  a seven eight nine test"),
                         "it is 7 8 9 test")
        self.assertEqual(normalize("it's a seven eight nine  test"),
                         "it is 7 8 9 test")
        self.assertEqual(normalize("that's a ten eleven twelve test"),
                         "that is 10 11 12 test")
        self.assertEqual(normalize("that's a thirteen fourteen test"),
                         "that is 13 14 test")
        self.assertEqual(normalize("that's fifteen sixteen seventeen"),
                         "that is 15 16 17")
        self.assertEqual(normalize("that's eighteen nineteen twenty"),
                         "that is 18 19 20")

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

    # Pt-pt
    def test_articles_pt(self):
        self.assertEqual(normalize(u"isto é o teste",
                                   lang="pt", remove_articles=True),
                         u"isto teste")
        self.assertEqual(
            normalize(u"isto é a frase", lang="pt", remove_articles=True),
            u"isto frase")
        self.assertEqual(
            normalize("e outro teste", lang="pt", remove_articles=True),
            "outro teste")
        self.assertEqual(normalize(u"isto é o teste extra",
                                   lang="pt",
                                   remove_articles=False), u"isto e o teste"
                                                           u" extra")

    def test_extractnumber_pt(self):
        self.assertEqual(extractnumber("isto e o primeiro teste", lang="pt"),
                         1)
        self.assertEqual(extractnumber("isto e o 2 teste", lang="pt"), 2)
        self.assertEqual(extractnumber("isto e o segundo teste", lang="pt"),
                         2)
        self.assertEqual(extractnumber(u"isto e um terço de teste",
                                       lang="pt"), 1.0 / 3.0)
        self.assertEqual(extractnumber("isto e o teste numero quatro",
                                       lang="pt"), 4)
        self.assertEqual(extractnumber(u"um terço de chavena", lang="pt"),
                         1.0 / 3.0)
        self.assertEqual(extractnumber("3 canecos", lang="pt"), 3)
        self.assertEqual(extractnumber("1/3 canecos", lang="pt"), 1.0 / 3.0)
        self.assertEqual(extractnumber("quarto de hora", lang="pt"), 0.25)
        self.assertEqual(extractnumber("1/4 hora", lang="pt"), 0.25)
        self.assertEqual(extractnumber("um quarto hora", lang="pt"), 0.25)
        self.assertEqual(extractnumber("2/3 pinga", lang="pt"), 2.0 / 3.0)
        self.assertEqual(extractnumber("3/4 pinga", lang="pt"), 3.0 / 4.0)
        self.assertEqual(extractnumber("1 e 3/4 cafe", lang="pt"), 1.75)
        self.assertEqual(extractnumber("1 cafe e meio", lang="pt"), 1.5)
        self.assertEqual(extractnumber("um cafe e um meio", lang="pt"), 1.5)
        self.assertEqual(
            extractnumber("tres quartos de chocolate", lang="pt"),
            3.0 / 4.0)
        self.assertEqual(extractnumber(u"trï¿½s quarto de chocolate",
                                       lang="pt"), 3.0 / 4.0)
        self.assertEqual(extractnumber("sete ponto cinco", lang="pt"), 7.5)
        self.assertEqual(extractnumber("sete ponto 5", lang="pt"), 7.5)
        self.assertEqual(extractnumber("sete e meio", lang="pt"), 7.5)
        self.assertEqual(extractnumber("sete e oitenta", lang="pt"), 7.80)
        self.assertEqual(extractnumber("sete e oito", lang="pt"), 7.8)
        self.assertEqual(extractnumber("sete e zero oito",
                                       lang="pt"), 7.08)
        self.assertEqual(extractnumber("sete e zero zero oito",
                                       lang="pt"), 7.008)
        self.assertEqual(extractnumber("vinte treze avos", lang="pt"),
                         20.0 / 13.0)
        self.assertEqual(extractnumber("seis virgula seiscentos e sessenta",
                                       lang="pt"), 6.66)
        self.assertEqual(extractnumber("seiscentos e sessenta e seis",
                                       lang="pt"), 666)

        self.assertEqual(extractnumber("seiscentos ponto zero seis",
                                       lang="pt"), 600.06)
        self.assertEqual(extractnumber("seiscentos ponto zero zero seis",
                                       lang="pt"), 600.006)
        self.assertEqual(extractnumber("seiscentos ponto zero zero zero seis",
                                       lang="pt"), 600.0006)

    def test_agressive_pruning_pt(self):
        self.assertEqual(normalize("uma palavra", lang="pt"),
                         "1 palavra")
        self.assertEqual(normalize("esta palavra um", lang="pt"),
                         "palavra 1")
        self.assertEqual(normalize("o homem batia-lhe", lang="pt"),
                         "homem batia")
        self.assertEqual(normalize("quem disse asneira nesse dia", lang="pt"),
                         "quem disse asneira dia")

    def test_spaces_pt(self):
        self.assertEqual(normalize("  isto   e  o    teste", lang="pt"),
                         "isto teste")
        self.assertEqual(normalize("  isto   sao os    testes  ", lang="pt"),
                         "isto sao testes")
        self.assertEqual(normalize("  isto   e  um    teste", lang="pt",
                                   remove_articles=False),
                         "isto e 1 teste")

    def test_numbers_pt(self):
        self.assertEqual(normalize(u"isto e o um dois trï¿½s teste", lang="pt"),
                         u"isto 1 2 3 teste")
        self.assertEqual(normalize(u"ï¿½ a sete oito nove  test", lang="pt"),
                         u"7 8 9 test")
        self.assertEqual(
            normalize("teste zero dez onze doze treze", lang="pt"),
            "teste 0 10 11 12 13")
        self.assertEqual(
            normalize("teste mil seiscentos e sessenta e seis", lang="pt",
                      remove_articles=False),
            "teste 1000 600 e 66")
        self.assertEqual(
            normalize("teste sete e meio", lang="pt",
                      remove_articles=False),
            "teste 7 e meio")
        self.assertEqual(
            normalize("teste dois ponto nove", lang="pt"),
            "teste 2 ponto 9")
        self.assertEqual(
            normalize("teste cento e nove", lang="pt",
                      remove_articles=False),
            "teste 100 e 9")
        self.assertEqual(
            normalize("teste vinte e 1", lang="pt"),
            "teste 20 1")

    def test_extractdatetime_pt(self):
        def extractWithFormat(text):
            date = datetime(2017, 06, 27, 00, 00)
            [extractedDate, leftover] = extract_datetime(text, date,
                                                         lang="pt")
            extractedDate = extractedDate.strftime("%Y-%m-%d %H:%M:%S")
            return [extractedDate, leftover]

        def testExtract(text, expected_date, expected_leftover):
            res = extractWithFormat(text)
            self.assertEqual(res[0], expected_date)
            self.assertEqual(res[1], expected_leftover)

        testExtract(u"que dia ï¿½ hoje",
                    "2017-06-27 00:00:00", u"dia")
        testExtract(u"que dia ï¿½ amanha",
                    "2017-06-28 00:00:00", u"dia")
        testExtract(u"que dia foi ontem",
                    "2017-06-26 00:00:00", u"dia")
        testExtract(u"que dia foi antes de ontem",
                    "2017-06-25 00:00:00", u"dia")
        testExtract(u"que dia foi ante ontem",
                    "2017-06-25 00:00:00", u"dia")
        testExtract(u"que dia foi ante ante ontem",
                    "2017-06-24 00:00:00", u"dia")
        testExtract("marca o jantar em 5 dias",
                    "2017-07-02 00:00:00", "marca jantar")
        testExtract("como esta o tempo para o dia depois de amanha?",
                    "2017-06-29 00:00:00", "como tempo")
        testExtract(u"lembra me ás 10:45 pm",
                    "2017-06-27 22:45:00", u"lembra")
        testExtract("como esta o tempo na sexta de manha",
                    "2017-06-30 08:00:00", "como tempo")
        testExtract(u"lembra me para ligar a mãe daqui "
                    u"a 8 semanas e 2 dias",
                    "2017-08-24 00:00:00", u"lembra ligar mae")
        testExtract("Toca black metal 2 dias a seguir a sexta",
                    "2017-07-02 00:00:00", "toca black metal")
        testExtract("Toca satanic black metal 2 dias para esta sexta",
                    "2017-07-02 00:00:00", "toca satanic black metal")
        testExtract("Toca super black metal 2 dias a partir desta sexta",
                    "2017-07-02 00:00:00", "toca super black metal")
        testExtract(u"Começa a invasão ás 3:45 pm de quinta feira",
                    "2017-06-29 15:45:00", "comeca invasao")
        testExtract("na segunda, compra queijo",
                    "2017-07-03 00:00:00", "compra queijo")
        testExtract(u"Toca os parabéns daqui a 5 anos",
                    "2022-06-27 00:00:00", "toca parabens")
        testExtract(u"manda Skype a Mãe ás 12:45 pm próxima quinta",
                    "2017-06-29 12:45:00", "manda skype mae")
        testExtract(u"como está o tempo esta sexta?",
                    "2017-06-30 00:00:00", "como tempo")
        testExtract(u"como está o tempo esta sexta de tarde?",
                    "2017-06-30 15:00:00", "como tempo")
        testExtract(u"como está o tempo esta sexta as tantas da manha?",
                    "2017-06-30 04:00:00", "como tempo")
        testExtract(u"como está o tempo esta sexta a meia noite?",
                    "2017-06-30 00:00:00", "como tempo")
        testExtract(u"como está o tempo esta sexta ao meio dia?",
                    "2017-06-30 12:00:00", "como tempo")
        testExtract(u"como está o tempo esta sexta ao fim da tarde?",
                    "2017-06-30 19:00:00", "como tempo")
        testExtract(u"como está o tempo esta sexta ao meio da manha?",
                    "2017-06-30 10:00:00", "como tempo")
        testExtract("lembra me para ligar a mae no dia 3 de agosto",
                    "2017-08-03 00:00:00", "lembra ligar mae")

        testExtract(u"compra facas no 13ï¿½ dia de maio",
                    "2018-05-13 00:00:00", "compra facas")
        testExtract(u"gasta dinheiro no maio dia 13",
                    "2018-05-13 00:00:00", "gasta dinheiro")
        testExtract(u"compra velas a maio 13",
                    "2018-05-13 00:00:00", "compra velas")
        testExtract(u"bebe cerveja a 13 maio",
                    "2018-05-13 00:00:00", "bebe cerveja")
        testExtract("como esta o tempo 1 dia a seguir a amanha",
                    "2017-06-29 00:00:00", "como tempo")
        testExtract(u"como esta o tempo ás 0700 horas",
                    "2017-06-27 07:00:00", "como tempo")
        testExtract(u"como esta o tempo amanha ás 7 em ponto",
                    "2017-06-28 07:00:00", "como tempo")
        testExtract(u"como esta o tempo amanha pelas 2 da tarde",
                    "2017-06-28 14:00:00", "como tempo")
        testExtract(u"como esta o tempo amanha pelas 2",
                    "2017-06-28 02:00:00", "como tempo")
        testExtract(u"como esta o tempo pelas 2 da tarde da proxima sexta",
                    "2017-06-30 14:00:00", "como tempo")
        testExtract("lembra-me de acordar em 4 anos",
                    "2021-06-27 00:00:00", "lembra acordar")
        testExtract("lembra-me de acordar em 4 anos e 4 dias",
                    "2021-07-01 00:00:00", "lembra acordar")
        testExtract("dorme 3 dias depois de amanha",
                    "2017-07-02 00:00:00", "dorme")
        testExtract("marca consulta para 2 semanas e 6 dias depois de Sabado",
                    "2017-07-21 00:00:00", "marca consulta")
        testExtract(u"começa a festa ás 8 em ponto da noite de quinta",
                    "2017-06-29 20:00:00", "comeca festa")

    def test_gender_pt(self):
        self.assertEqual(get_gender("vaca", lang="pt"),
                         "f")
        self.assertEqual(get_gender("cavalo", lang="pt"),
                         "m")
        self.assertEqual(get_gender("vacas", lang="pt"),
                         "f")
        self.assertEqual(get_gender("boi", "o boi come erva", lang="pt"),
                         "m")
        self.assertEqual(get_gender("boi", lang="pt"),
                         False)
        self.assertEqual(get_gender("homem", "estes homem come merda",
                                    lang="pt"),
                         "m")
        self.assertEqual(get_gender("ponte", lang="pt"),
                         "m")
        self.assertEqual(get_gender("ponte", "essa ponte caiu",
                                    lang="pt"),
                         "f")

    #
    # Spanish
    #
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
        self.assertEqual(normalize(u"diecisï¿½is diecisiete", lang="es"),
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
            u"ciento veintitrï¿½s mil cuatrocientas cincuenta y seis",
            lang="es"),
            "123456")
        self.assertEqual(normalize(
            u"quinientas veinticinco mil", lang="es"),
            "525000")
        self.assertEqual(normalize(
            u"novecientos noventa y nueve mil novecientos noventa y nueve",
            lang="es"),
            "999999")


    #
    # Italian
    #

    def test_gender_it(self):
        self.assertEqual(get_gender("mucca", lang="it-it"),
                         "f")
        self.assertEqual(get_gender("cavallo", lang="it-it"),
                         "m")
        self.assertEqual(get_gender("mucche", "le mucche", lang="it-it"),
                         "f")
        self.assertEqual(get_gender("bue", "il bue mangia la erba",
                                    lang="it-it"), "m")
        self.assertEqual(get_gender("pesce", "il pesce nuota", lang="it-it"),
                         "m")
        self.assertEqual(get_gender("tigre", lang="it-it"), "f")

        self.assertEqual(get_gender("uomini", "questi uomini mangiano pasta",
                                    lang="it-it"), "m")
        self.assertEqual(get_gender("ponte", "il ponte", lang="it-it"),
                         "m")
        self.assertEqual(get_gender("ponte", u"questo ponte è caduto",
                                    lang="it-it"), "m")
        self.assertEqual(get_gender("scultrice", "questa scultrice famosa",
                                    lang="it-it"), "f")
        self.assertEqual(get_gender("scultore", "questo scultore famoso",
                                    lang="it-it"), "m")
        self.assertEqual(get_gender("scultori", "gli scultori rinascimentali",
                                    lang="it-it"), "m")
        self.assertEqual(get_gender("scultrici", "le scultrici rinascimentali",
                                    lang="it-it"), "f")


if __name__ == "__main__":
    unittest.main()
