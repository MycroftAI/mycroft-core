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
"""
    Parse functions for Italian (IT-IT)

    TODO: numbers greater than 999999
    TODO: it_number_parse
    TODO: extract_datetime_it
    TODO: it_pruning

"""


from mycroft.util.lang.parse_common import is_numeric, look_for_fractions


# Undefined articles ["un", "una", "un'"] can not be supressed,
# in Italian, "un cavallo" means "a horse" or "one horse".
it_articles = ["il", "lo", "la"]

it_numbers = {
    "zero": 0,
    "un": 1,
    "uno": 1,
    "una": 1,
    "un'": 1,
    "due": 2,
    "tre": 3,
    "quattro": 4,
    "cinque": 5,
    "sei": 6,
    "sette": 7,
    "otto": 8,
    "nove": 9,
    "dieci": 10,
    "undici": 11,
    "dodici": 12,
    "tredici": 13,
    "quattordici": 14,
    "quindici": 15,
    "sedici": 16,
    "diciassette": 17,
    "diciotto": 18,
    "diciannove": 19,
    "venti": 20,
    "trenta": 30,
    "quaranta": 40,
    "cinquanta": 50,
    "sessanta": 60,
    "settanta": 70,
    "ottanta": 80,
    "novanta": 90,
    "cento": 100,
    "duecento": 200,
    "trecento": 300,
    "quattrocento": 400,
    "cinquecento": 500,
    "seicento": 600,
    "settecento": 700,
    "ottocento": 800,
    "novecento": 900,
    "primo": 1,
    "secondo": 2,
    "mille": 1000,
    "mila": 1000
}


def isFractional_it(input_str):
    """
    This function takes the given text and checks if it is a fraction.
    E' la versione portoghese riadattata in italiano

    Args:
        text (str): the string to check if fractional
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    TODO:  verificare la corretta gestione dei plurali
    """

    aFrac = ["mezz", "terz", "quart", "quint", "sest", "settim", "ottav",
             "non", "decim", "undicesim", "dodicesim", "tredicesim",
             "quattrodicesim", "quindicesim", "sedicesim",
             "diciasettesim", "diciottesim", "diciasettesim",
             "diciannovesim"]

    if input_str[:-1].lower() in aFrac:
        return 1.0 / (aFrac.index(input_str[:-1]) + 2)
    if input_str[:-1] == "ventesim":
        return 1.0 / 20
    if input_str[:-1] == "centesim":
        return 1.0 / 100
    if input_str[:-1] == "millesim":
        return 1.0 / 1000

    return False


def extractnumber_it(text):
    """
    Questa funzione prepara il testo dato per l'analisi rendendo
    numeri testuali come interi o frazioni.
    In italiano non è un modo abituale ma può essere interessante
    per Mycroft
    E' la versione portoghese riadattata in italiano
     args:
         text (str): la stringa da normalizzare
    Ritorna:
         (int) o (float): il valore del numero estratto

    """
    aWords = text.split()
    count = 0
    result = None
    while count < len(aWords):
        val = 0
        word = aWords[count]
        next_next_word = None
        if count + 1 < len(aWords):
            next_word = aWords[count + 1]
            if count + 2 < len(aWords):
                next_next_word = aWords[count + 2]
        else:
            next_word = None

        # is current word a number?
        if word in it_numbers:
            if word == "mila":
                val = it_numbers[word]
                val = result * val
                result = 0
            else:
                val = it_numbers[word]

        elif word.isdigit():  # doesn't work with decimals
            val = int(word)
        elif is_numeric(word):
            val = float(word)

        elif isFractional_it(word):
            if not result:
                result = 1
            result = result * isFractional_it(word)
            # "un terzo" is 1/3 but "il terzo" is 3
            if aWords[count - 1] == "il":
                result = 1.0 // isFractional_it(word)

            count += 1
            continue

        if not val:
            # look for fractions like "2/3"
            aPieces = word.split('/')
            # if (len(aPieces) == 2 and is_numeric(aPieces[0])
            #   and is_numeric(aPieces[1])):
            if look_for_fractions(aPieces):
                val = float(aPieces[0]) / float(aPieces[1])

        if val:
            if result is None:
                result = 0
            # handle fractions
            # if next_word != "avos":
            result += val
            # else:
            #    result = float(result) / float(val)

        if next_word is None:
            break

        # number word and fraction
        ands = ["e"]
        if next_word in ands:
            zeros = 0
            if result is None:
                count += 1
                continue
            newWords = aWords[count + 2:]
            newText = ""
            for word in newWords:
                newText += word + " "

            afterAndVal = extractnumber_it(newText[:-1])
            if afterAndVal:
                if result < afterAndVal or result < 20:
                    while afterAndVal > 1:
                        afterAndVal = afterAndVal / 10.0
                    for word in newWords:
                        if word == "zero" or word == "0":
                            zeros += 1
                        else:
                            break
                for _ in range(0, zeros):
                    afterAndVal = afterAndVal / 10.0
                result += afterAndVal
                break
        elif next_next_word is not None:
            if next_next_word in ands:
                newWords = aWords[count + 3:]
                newText = ""
                for word in newWords:
                    newText += word + " "
                afterAndVal = extractnumber_it(newText[:-1])
                if afterAndVal:
                    if result is None:
                        result = 0
                    result += afterAndVal
                    break

        decimals = ["punto", "virgola", ".", ","]
        if next_word in decimals:
            zeros = 0
            newWords = aWords[count + 2:]
            newText = ""
            for word in newWords:
                newText += word + " "
            for word in newWords:
                if word == "zero" or word == "0":
                    zeros += 1
                else:
                    break
            afterDotVal = str(extractnumber_it(newText[:-1]))
            afterDotVal = zeros * "0" + afterDotVal
            result = float(str(result) + "." + afterDotVal)
            break
        count += 1

    if result is None:
        return False

    # Return the $str with the number related words removed
    # (now empty strings, so strlen == 0)
    # aWords = [word for word in aWords if len(word) > 0]
    # text = ' '.join(aWords)
    if "." in str(result):
        integer, dec = str(result).split(".")
        # cast float to int
        if dec == "0":
            result = int(integer)

    return result


def normalize_it(text, remove_articles):
    """ IT string normalization """

    words = text.split()  # this also removed extra spaces
    # Contractions are not common in IT
    # Convert numbers into digits, e.g. "due" -> "2"
    normalized = ""
    i = 0

    while i < len(words):
        word = words[i]
        # remove articles
        # Italian requires the article to define the gender of the next word
        if remove_articles and word in it_articles:
            i += 1
            continue

        # NOTE temporary , handle some numbers above >999
        if word in it_numbers:
            word = str(it_numbers[word])
        # end temporary

        normalized += " " + word
        i += 1
    # indefinite articles in it-it can not be removed

    return normalized[1:]


def get_gender_it(word, raw_string=""):
    """
    Questa potrebbe non essere utile.
    In italiano per definire il genere è necessario
    analizzare l'articolo che la precede e non la lettera
    con cui finisce la parola, ma sono presenti funzioni per
    la rimozione degli articoli dalla frase per semplificarne
    l'analisi, in particolare se si rimuovono "i", "gli", "le"

    TODO:  verificare se utile
    """

    gender = False
    words = raw_string.split(" ")
    for idx, w in enumerate(words):
        if w == word and idx != 0:
            previous = words[idx - 1]
            gender = get_gender_it(previous)
            break

    if not gender:
        if word[-1] == "a" or word[-1] == "e":
            gender = "f"
        if word[-1] == "o" or word[-1] == "n" \
                or word[-1] == "l" or word[-1] == "i":
            gender = "m"

    return gender
