
# -*- coding: iso-8859-15 -*-

# Copyright 2017 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


def normalize(text, lang="en-us", remove_articles=True):
    """Prepare a string for parsing

    This function prepares the given text for parsing by making
    numbers consistent, getting rid of contractions, etc.
    Args:
        text (str): the string to normalize
        lang (str): the code for the language text is in
        remove_articles (bool): whether to remove articles (like 'a', or 'the')
    Returns:
        (str): The normalized string.
    """

    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return normalize_en(text, remove_articles)
    elif lang_lower.startswith("es"):
        return normalize_es(text, remove_articles)

    # TODO: Normalization for other languages
    return text


def normalize_en(text, remove_articles):
    """ English string normalization """

    words = text.split()  # this also removed extra spaces
    normalized = ""
    for word in words:
        if remove_articles and word in ["the", "a", "an"]:
            continue

        # Expand common contractions, e.g. "isn't" -> "is not"
        contraction = ["ain't", "aren't", "can't", "could've", "couldn't",
                       "didn't", "doesn't", "don't", "gonna", "gotta",
                       "hadn't", "hasn't", "haven't", "he'd", "he'll", "he's",
                       "how'd", "how'll", "how's", "I'd", "I'll", "I'm",
                       "I've", "isn't", "it'd", "it'll", "it's", "mightn't",
                       "might've", "mustn't", "must've", "needn't", "oughtn't",
                       "shan't", "she'd", "she'll", "she's", "shouldn't",
                       "should've", "somebody's", "someone'd", "someone'll",
                       "someone's", "that'll", "that's", "that'd", "there'd",
                       "there're", "there's", "they'd", "they'll", "they're",
                       "they've", "wasn't", "we'd", "we'll", "we're", "we've",
                       "weren't", "what'd", "what'll", "what're", "what's",
                       "whats",  # technically incorrect but some STT does this
                       "what've", "when's", "when'd", "where'd", "where's",
                       "where've", "who'd", "who'd've", "who'll", "who're",
                       "who's", "who've", "why'd", "why're", "why's", "won't",
                       "won't've", "would've", "wouldn't", "wouldn't've",
                       "y'all", "ya'll", "you'd", "you'd've", "you'll",
                       "y'aint", "y'ain't", "you're", "you've"]
        if word in contraction:
            expansion = ["is not", "are not", "can not", "could have",
                         "could not", "did not", "does not", "do not",
                         "going to", "got to", "had not", "has not",
                         "have not", "he would", "he will", "he is", "how did",
                         "how will", "how is", "I would", "I will", "I am",
                         "I have", "is not", "it would", "it will", "it is",
                         "might not", "might have", "must not", "must have",
                         "need not", "ought not", "shall not", "she would",
                         "she will", "she is", "should not", "should have",
                         "somebody is", "someone would", "someone will",
                         "someone is", "that will", "that is", "that would",
                         "there would", "there are", "there is", "they would",
                         "they will", "they are", "they have", "was not",
                         "we would", "we will", "we are", "we have",
                         "were not", "what did", "what will", "what are",
                         "what is",
                         "what is", "what have", "when is", "when did",
                         "where did", "where is", "where have", "who would",
                         "who would have", "who will", "who are", "who is",
                         "who have", "why did", "why are", "why is",
                         "will not", "will not have", "would have",
                         "would not", "would not have", "you all", "you all",
                         "you would", "you would have", "you will",
                         "you are not", "you are not", "you are", "you have"]
            word = expansion[contraction.index(word)]

        # Convert numbers into digits, e.g. "two" -> "2"
        textNumbers = ["zero", "one", "two", "three", "four", "five", "six",
                       "seven", "eight", "nine", "ten", "eleven", "twelve",
                       "thirteen", "fourteen", "fifteen", "sixteen",
                       "seventeen", "eighteen", "nineteen", "twenty"]
        if word in textNumbers:
            word = str(textNumbers.index(word))

        normalized += " " + word

    return normalized[1:]  # strip the initial space


####################################################################
# Spanish normalization
#
# TODO: numbers greater than 999999
####################################################################

# Undefined articles ["un", "una", "unos", "unas"] can not be supressed,
# in Spanish, "un caballo" means "a horse" or "one horse".
es_articles = ["el", "la", "los", "las"]

es_numbers_xlat = {
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    u"dieciséis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiuno": 21,
    u"veintidós": 22,
    u"veintitrés": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    u"veintiséis": 26,
    "veintisiete": 27,
    "veintiocho": 28,
    "veintinueve": 29,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
    "cien": 100,
    "ciento": 100,
    "doscientos": 200,
    "doscientas": 200,
    "trescientos": 300,
    "trescientas": 300,
    "cuatrocientos": 400,
    "cuatrocientas": 400,
    "quinientos": 500,
    "quinientas": 500,
    "seiscientos": 600,
    "seiscientas": 600,
    "setecientos": 700,
    "setecientas": 700,
    "ochocientos": 800,
    "ochocientas": 800,
    "novecientos": 900,
    "novecientas": 900}


def es_parse(words, i):
    def es_cte(i, s):
        if i < len(words) and s == words[i]:
            return s, i+1
        return None

    def es_number_word(i, mi, ma):
        if i < len(words):
            v = es_numbers_xlat.get(words[i])
            if v and v >= mi and v <= ma:
                return v, i+1
        return None

    def es_number_1_99(i):
        r1 = es_number_word(i, 1, 29)
        if r1:
            return r1

        r1 = es_number_word(i, 30, 90)
        if r1:
            v1, i1 = r1
            r2 = es_cte(i1, "y")
            if r2:
                v2, i2 = r2
                r3 = es_number_word(i2, 1, 9)
                if r3:
                    v3, i3 = r3
                    return v1+v3, i3
            return r1
        return None

    def es_number_1_999(i):
        # [2-9]cientos [1-99]?
        r1 = es_number_word(i, 100, 900)
        if r1:
            v1, i1 = r1
            r2 = es_number_1_99(i1)
            if r2:
                v2, i2 = r2
                return v1+v2, i2
            else:
                return r1

        # [1-99]
        r1 = es_number_1_99(i)
        if r1:
            return r1

        return None

    def es_number(i):
        # check for cero
        r1 = es_number_word(i, 0, 0)
        if r1:
            return r1

        # check for [1-999] (mil [0-999])?
        r1 = es_number_1_999(i)
        if r1:
            v1, i1 = r1
            r2 = es_cte(i1, "mil")
            if r2:
                v2, i2 = r2
                r3 = es_number_1_999(i2)
                if r3:
                    v3, i3 = r3
                    return v1*1000+v3, i3
                else:
                    return v1*1000, i2
            else:
                return r1
        return None

    return es_number(i)


def normalize_es(text, remove_articles):
    """ Spanish string normalization """

    words = text.split()  # this also removed extra spaces

    normalized = ""
    i = 0
    while i < len(words):
        word = words[i]

        if remove_articles and word in es_articles:
            i += 1
            continue

        # Convert numbers into digits
        r = es_parse(words, i)
        if r:
            v, i = r
            normalized += " " + str(v)
            continue

        normalized += " " + word
        i += 1

    return normalized[1:]  # strip the initial space
