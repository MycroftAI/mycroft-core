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
    Parse functions for Portuguese (PT-PT)

    TODO: numbers greater than 999999
    TODO: date time pt
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
from mycroft.util.lang.parse_common import is_numeric, look_for_fractions


# Undefined articles ["um", "uma", "uns", "umas"] can not be supressed,
# in PT, "um cavalo" means "a horse" or "one horse".
pt_articles = ["o", "a", "os", "as"]

pt_numbers = {
    "zero": 0,
    "um": 1,
    "uma": 1,
    "uns": 1,
    "umas": 1,
    "primeiro": 1,
    "segundo": 2,
    "terceiro": 3,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    u"três": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "onze": 11,
    "doze": 12,
    "treze": 13,
    "catorze": 14,
    "quinze": 15,
    "dezasseis": 16,
    "dezassete": 17,
    "dezoito": 18,
    "dezanove": 19,
    "vinte": 20,
    "trinta": 30,
    "quarenta": 40,
    "cinquenta": 50,
    "sessenta": 60,
    "setenta": 70,
    "oitenta": 80,
    "noventa": 90,
    "cem": 100,
    "cento": 100,
    "duzentos": 200,
    "duzentas": 200,
    "trezentos": 300,
    "trezentas": 300,
    "quatrocentos": 400,
    "quatrocentas": 400,
    "quinhentos": 500,
    "quinhentas": 500,
    "seiscentos": 600,
    "seiscentas": 600,
    "setecentos": 700,
    "setecentas": 700,
    "oitocentos": 800,
    "oitocentas": 800,
    "novecentos": 900,
    "novecentas": 900,
    "mil": 1000,
    u"milhï¿½o": 1000000}


def isFractional_pt(input_str):
    """
    This function takes the given text and checks if it is a fraction.

    Args:
        text (str): the string to check if fractional
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    if input_str.endswith('s', -1):
        input_str = input_str[:len(input_str) - 1]  # e.g. "fifths"

    aFrac = ["meio", u"terço", "quarto", "quinto", "sexto",
             "setimo", "oitavo", "nono", u"décimo"]

    if input_str.lower() in aFrac:
        return 1.0 / (aFrac.index(input_str) + 2)
    if input_str == u"vigésimo":
        return 1.0 / 20
    if input_str == u"trigésimo":
        return 1.0 / 30
    if input_str == u"centésimo":
        return 1.0 / 100
    if input_str == u"milésimo":
        return 1.0 / 1000
    if (input_str == u"sétimo" or input_str == "septimo" or
            input_str == u"séptimo"):
        return 1.0 / 7

    return False


def extractnumber_pt(text):
    """
    This function prepares the given text for parsing by making
    numbers consistent, getting rid of contractions, etc.
    Args:
        text (str): the string to normalize
    Returns:
        (int) or (float): The value of extracted number

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
        if word in pt_numbers:
            val = pt_numbers[word]
        elif word.isdigit():  # doesn't work with decimals
            val = int(word)
        elif is_numeric(word):
            val = float(word)
        elif isFractional_pt(word):
            if not result:
                result = 1
            result = result * isFractional_pt(word)
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
            if next_word != "avos":
                result += val
            else:
                result = float(result) / float(val)

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

            afterAndVal = extractnumber_pt(newText[:-1])
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
                afterAndVal = extractnumber_pt(newText[:-1])
                if afterAndVal:
                    if result is None:
                        result = 0
                    result += afterAndVal
                    break

        decimals = ["ponto", "virgula", u"vï¿½rgula", ".", ","]
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
            afterDotVal = str(extractnumber_pt(newText[:-1]))
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


def pt_number_parse(words, i):
    def pt_cte(i, s):
        if i < len(words) and s == words[i]:
            return s, i + 1
        return None

    def pt_number_word(i, mi, ma):
        if i < len(words):
            v = pt_numbers.get(words[i])
            if v and v >= mi and v <= ma:
                return v, i + 1
        return None

    def pt_number_1_99(i):
        r1 = pt_number_word(i, 1, 29)
        if r1:
            return r1

        r1 = pt_number_word(i, 30, 90)
        if r1:
            v1, i1 = r1
            r2 = pt_cte(i1, "e")
            if r2:
                i2 = r2[1]
                r3 = pt_number_word(i2, 1, 9)
                if r3:
                    v3, i3 = r3
                    return v1 + v3, i3
            return r1
        return None

    def pt_number_1_999(i):
        # [2-9]cientos [1-99]?
        r1 = pt_number_word(i, 100, 900)
        if r1:
            v1, i1 = r1
            r2 = pt_number_1_99(i1)
            if r2:
                v2, i2 = r2
                return v1 + v2, i2
            else:
                return r1

        # [1-99]
        r1 = pt_number_1_99(i)
        if r1:
            return r1

        return None

    def pt_number(i):
        # check for cero
        r1 = pt_number_word(i, 0, 0)
        if r1:
            return r1

        # check for [1-999] (mil [0-999])?
        r1 = pt_number_1_999(i)
        if r1:
            v1, i1 = r1
            r2 = pt_cte(i1, "mil")
            if r2:
                i2 = r2[1]
                r3 = pt_number_1_999(i2)
                if r3:
                    v3, i3 = r3
                    return v1 * 1000 + v3, i3
                else:
                    return v1 * 1000, i2
            else:
                return r1
        return None

    return pt_number(i)


def normalize_pt(text, remove_articles):
    """ PT string normalization """

    words = text.split()  # this also removed extra spaces
    normalized = ""
    # Contractions are not common in PT

    # Convert numbers into digits, e.g. "dois" -> "2"
    normalized = ""
    i = 0
    while i < len(words):
        word = words[i]
        # remove articles
        if remove_articles and word in pt_articles:
            i += 1
            continue

        # Convert numbers into digits
        r = pt_number_parse(words, i)
        if r:
            v, i = r
            normalized += " " + str(v)
            continue

        # NOTE temporary , handle some numbers above >999
        if word in pt_numbers:
            word = str(pt_numbers[word])
        # end temporary

        normalized += " " + word
        i += 1
    # some articles in pt-pt can not be removed, but many words can
    # this is experimental and some meaning may be lost
    # maybe agressive should default to False
    # only usage will tell, as a native speaker this seems reasonable
    return pt_pruning(normalized[1:], agressive=remove_articles)


def extract_datetime_pt(input_str, currentDate=None):
    def clean_string(s):
        # cleans the input string of unneeded punctuation and capitalization
        # among other things
        symbols = [".", ",", ";", "?", "!", u"º", u"ª"]
        noise_words = ["o", "os", "a", "as", "do", "da", "dos", "das", "de",
                       "ao", "aos"]

        for word in symbols:
            s = s.replace(word, "")
        for word in noise_words:
            s = s.replace(" " + word + " ", " ")
        s = s.lower().replace(
            u"á",
            "a").replace(
            u"ç",
            "c").replace(
            u"à",
            "a").replace(
            u"ã",
            "a").replace(
            u"é",
            "e").replace(
            u"è",
            "e").replace(
            u"ê",
            "e").replace(
            u"ó",
            "o").replace(
            u"ò",
            "o").replace(
            "-",
            " ").replace(
            "_",
            "")
        # handle synonims and equivalents, "tomorrow early = tomorrow morning
        synonims = {"manha": ["manhazinha", "cedo", "cedinho"],
                    "tarde": ["tardinha", "tarde"],
                    "noite": ["noitinha", "anoitecer"],
                    "todos": ["ao", "aos"],
                    "em": ["do", "da", "dos", "das", "de"]}
        for syn in synonims:
            for word in synonims[syn]:
                s = s.replace(" " + word + " ", " " + syn + " ")
        # relevant plurals, cant just extract all s in pt
        wordlist = ["manhas", "noites", "tardes", "dias", "semanas", "anos",
                    "minutos", "segundos", "nas", "nos", "proximas",
                    "seguintes", "horas"]
        for _, word in enumerate(wordlist):
            s = s.replace(word, word.rstrip('s'))
        s = s.replace("meses", "mes").replace("anteriores", "anterior")
        return s

    def date_found():
        return found or \
            (
                datestr != "" or timeStr != "" or
                yearOffset != 0 or monthOffset != 0 or
                dayOffset is True or hrOffset != 0 or
                hrAbs != 0 or minOffset != 0 or
                minAbs != 0 or secOffset != 0
            )

    if input_str == "":
        return None
    if currentDate is None:
        currentDate = datetime.now()

    found = False
    daySpecified = False
    dayOffset = False
    monthOffset = 0
    yearOffset = 0
    dateNow = currentDate
    today = dateNow.strftime("%w")
    currentYear = dateNow.strftime("%Y")
    fromFlag = False
    datestr = ""
    hasYear = False
    timeQualifier = ""

    words = clean_string(input_str).split(" ")
    timeQualifiersList = ['manha', 'tarde', 'noite']
    time_indicators = ["em", "as", "nas", "pelas", "volta", "depois", "estas",
                       "no", "dia", "hora"]
    days = ['segunda', 'terca', 'quarta',
            'quinta', 'sexta', 'sabado', 'domingo']
    months = ['janeiro', 'febreiro', 'marco', 'abril', 'maio', 'junho',
              'julho', 'agosto', 'setembro', 'outubro', 'novembro',
              'dezembro']
    monthsShort = ['jan', 'feb', 'mar', 'abr', 'mai', 'jun', 'jul', 'ag',
                   'set', 'out', 'nov', 'dec']
    nexts = ["proximo", "proxima"]
    suffix_nexts = ["seguinte", "subsequente", "seguir"]
    lasts = ["ultimo", "ultima"]
    suffix_lasts = ["passada", "passado", "anterior", "antes"]
    nxts = ["depois", "seguir", "seguida", "seguinte", "proxima", "proximo"]
    prevs = ["antes", "ante", "previa", "previamente", "anterior"]
    froms = ["partir", "em", "para", "na", "no", "daqui", "seguir",
             "depois", "por", "proxima", "proximo", "da", "do", "de"]
    thises = ["este", "esta", "deste", "desta", "neste", "nesta", "nesse",
              "nessa"]
    froms += thises
    lists = nxts + prevs + froms + time_indicators
    for idx, word in enumerate(words):
        if word == "":
            continue
        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""
        wordNextNextNext = words[idx + 3] if idx + 3 < len(words) else ""

        start = idx
        used = 0
        # save timequalifier for later
        if word in timeQualifiersList:
            timeQualifier = word

        # parse today, tomorrow, yesterday
        elif word == "hoje" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "amanha" and not fromFlag:
            dayOffset = 1
            used += 1
        elif word == "ontem" and not fromFlag:
            dayOffset -= 1
            used += 1
        # "before yesterday" and "before before yesterday"
        elif (word == "anteontem" or
              (word == "ante" and wordNext == "ontem")) and not fromFlag:
            dayOffset -= 2
            used += 1
            if wordNext == "ontem":
                used += 1
        elif word == "ante" and wordNext == "ante" and wordNextNext == \
                "ontem" and not fromFlag:
            dayOffset -= 3
            used += 3
        elif word == "anteanteontem" and not fromFlag:
            dayOffset -= 3
            used += 1
        # day after tomorrow
        elif word == "depois" and wordNext == "amanha" and not fromFlag:
            dayOffset += 2
            used = 2
        # day before yesterday
        elif word == "antes" and wordNext == "ontem" and not fromFlag:
            dayOffset -= 2
            used = 2
        # parse 5 days, 10 weeks, last week, next week, week after
        elif word == "dia":
            if wordNext == "depois" or wordNext == "antes":
                used += 1
                if wordPrev and wordPrev[0].isdigit():
                    dayOffset += int(wordPrev)
                    start -= 1
                    used += 1
            elif (wordPrev and wordPrev[0].isdigit() and
                    wordNext not in months and
                    wordNext not in monthsShort):
                dayOffset += int(wordPrev)
                start -= 1
                used += 2
            elif wordNext and wordNext[0].isdigit() and wordNextNext not in \
                    months and wordNextNext not in monthsShort:
                dayOffset += int(wordNext)
                start -= 1
                used += 2

        elif word == "semana" and not fromFlag:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            for w in nexts:
                if wordPrev == w:
                    dayOffset = 7
                    start -= 1
                    used = 2
            for w in lasts:
                if wordPrev == w:
                    dayOffset = -7
                    start -= 1
                    used = 2
            for w in suffix_nexts:
                if wordNext == w:
                    dayOffset = 7
                    start -= 1
                    used = 2
            for w in suffix_lasts:
                if wordNext == w:
                    dayOffset = -7
                    start -= 1
                    used = 2
        # parse 10 months, next month, last month
        elif word == "mes" and not fromFlag:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            for w in nexts:
                if wordPrev == w:
                    monthOffset = 7
                    start -= 1
                    used = 2
            for w in lasts:
                if wordPrev == w:
                    monthOffset = -7
                    start -= 1
                    used = 2
            for w in suffix_nexts:
                if wordNext == w:
                    monthOffset = 7
                    start -= 1
                    used = 2
            for w in suffix_lasts:
                if wordNext == w:
                    monthOffset = -7
                    start -= 1
                    used = 2
        # parse 5 years, next year, last year
        elif word == "ano" and not fromFlag:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            for w in nexts:
                if wordPrev == w:
                    yearOffset = 7
                    start -= 1
                    used = 2
            for w in lasts:
                if wordPrev == w:
                    yearOffset = -7
                    start -= 1
                    used = 2
            for w in suffix_nexts:
                if wordNext == w:
                    yearOffset = 7
                    start -= 1
                    used = 2
            for w in suffix_lasts:
                if wordNext == w:
                    yearOffset = -7
                    start -= 1
                    used = 2
        # parse Monday, Tuesday, etc., and next Monday,
        # last Tuesday, etc.
        elif word in days and not fromFlag:

            d = days.index(word)
            dayOffset = (d + 1) - int(today)
            used = 1
            if dayOffset < 0:
                dayOffset += 7
            for w in nexts:
                if wordPrev == w:
                    dayOffset += 7
                    used += 1
                    start -= 1
            for w in lasts:
                if wordPrev == w:
                    dayOffset -= 7
                    used += 1
                    start -= 1
            for w in suffix_nexts:
                if wordNext == w:
                    dayOffset += 7
                    used += 1
                    start -= 1
            for w in suffix_lasts:
                if wordNext == w:
                    dayOffset -= 7
                    used += 1
                    start -= 1
            if wordNext == "feira":
                used += 1
        # parse 15 of July, June 20th, Feb 18, 19 of February
        elif word in months or word in monthsShort:
            try:
                m = months.index(word)
            except ValueError:
                m = monthsShort.index(word)
            used += 1
            datestr = months[m]
            if wordPrev and wordPrev[0].isdigit():
                # 13 maio
                datestr += " " + wordPrev
                start -= 1
                used += 1
                if wordNext and wordNext[0].isdigit():
                    datestr += " " + wordNext
                    used += 1
                    hasYear = True
                else:
                    hasYear = False

            elif wordNext and wordNext[0].isdigit():
                # maio 13
                datestr += " " + wordNext
                used += 1
                if wordNextNext and wordNextNext[0].isdigit():
                    datestr += " " + wordNextNext
                    used += 1
                    hasYear = True
                else:
                    hasYear = False

            elif wordPrevPrev and wordPrevPrev[0].isdigit():
                # 13 dia maio
                datestr += " " + wordPrevPrev

                start -= 2
                used += 2
                if wordNext and word[0].isdigit():
                    datestr += " " + wordNext
                    used += 1
                    hasYear = True
                else:
                    hasYear = False

            elif wordNextNext and wordNextNext[0].isdigit():
                # maio dia 13
                datestr += " " + wordNextNext
                used += 2
                if wordNextNextNext and wordNextNextNext[0].isdigit():
                    datestr += " " + wordNextNextNext
                    used += 1
                    hasYear = True
                else:
                    hasYear = False

            if datestr in months:
                datestr = ""

        # parse 5 days from tomorrow, 10 weeks from next thursday,
        # 2 months from July
        validFollowups = days + months + monthsShort
        validFollowups.append("hoje")
        validFollowups.append("amanha")
        validFollowups.append("ontem")
        validFollowups.append("anteontem")
        validFollowups.append("agora")
        validFollowups.append("ja")
        validFollowups.append("ante")

        # TODO debug word "depois" that one is failing for some reason
        if word in froms and wordNext in validFollowups:

            if not (wordNext == "amanha" and wordNext == "ontem") and not (
                    word == "depois" or word == "antes" or word == "em"):
                used = 2
                fromFlag = True
            if wordNext == "amanha" and word != "depois":
                dayOffset += 1
            elif wordNext == "ontem":
                dayOffset -= 1
            elif wordNext == "anteontem":
                dayOffset -= 2
            elif wordNext == "ante" and wordNextNext == "ontem":
                dayOffset -= 2
            elif (wordNext == "ante" and wordNext == "ante" and
                  wordNextNextNext == "ontem"):
                dayOffset -= 3
            elif wordNext in days:
                d = days.index(wordNext)
                tmpOffset = (d + 1) - int(today)
                used = 2
                if wordNextNext == "feira":
                    used += 1
                if tmpOffset < 0:
                    tmpOffset += 7
                if wordNextNext:
                    if wordNextNext in nxts:
                        tmpOffset += 7
                        used += 1
                    elif wordNextNext in prevs:
                        tmpOffset -= 7
                        used += 1
                dayOffset += tmpOffset
            elif wordNextNext and wordNextNext in days:
                d = days.index(wordNextNext)
                tmpOffset = (d + 1) - int(today)
                used = 3
                if wordNextNextNext:
                    if wordNextNextNext in nxts:
                        tmpOffset += 7
                        used += 1
                    elif wordNextNextNext in prevs:
                        tmpOffset -= 7
                        used += 1
                dayOffset += tmpOffset
                if wordNextNextNext == "feira":
                    used += 1
        if wordNext in months:
            used -= 1
        if used > 0:

            if start - 1 > 0 and words[start - 1] in lists:
                start -= 1
                used += 1

            for i in range(0, used):
                words[i + start] = ""

            if start - 1 >= 0 and words[start - 1] in lists:
                words[start - 1] = ""
            found = True
            daySpecified = True

    # parse time
    timeStr = ""
    hrOffset = 0
    minOffset = 0
    secOffset = 0
    hrAbs = 0
    minAbs = 0
    military = False

    for idx, word in enumerate(words):
        if word == "":
            continue

        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""
        wordNextNextNext = words[idx + 3] if idx + 3 < len(words) else ""
        # parse noon, midnight, morning, afternoon, evening
        used = 0
        if word == "meio" and wordNext == "dia":
            hrAbs = 12
            used += 2
        elif word == "meia" and wordNext == "noite":
            hrAbs = 0
            used += 2
        elif word == "manha":
            if hrAbs == 0:
                hrAbs = 8
            used += 1
        elif word == "tarde":
            if hrAbs == 0:
                hrAbs = 15
            used += 1
        elif word == "meio" and wordNext == "tarde":
            if hrAbs == 0:
                hrAbs = 17
            used += 2
        elif word == "meio" and wordNext == "manha":
            if hrAbs == 0:
                hrAbs = 10
            used += 2
        elif word == "fim" and wordNext == "tarde":
            if hrAbs == 0:
                hrAbs = 19
            used += 2
        elif word == "fim" and wordNext == "manha":
            if hrAbs == 0:
                hrAbs = 11
            used += 2
        elif word == "tantas" and wordNext == "manha":
            if hrAbs == 0:
                hrAbs = 4
            used += 2
        elif word == "noite":
            if hrAbs == 0:
                hrAbs = 22
            used += 1
        # parse half an hour, quarter hour
        elif word == "hora" and \
                (wordPrev in time_indicators or wordPrevPrev in
                    time_indicators):
            if wordPrev == "meia":
                minOffset = 30
            elif wordPrev == "quarto":
                minOffset = 15
            elif wordPrevPrev == "quarto":
                minOffset = 15
                if idx > 2 and words[idx - 3] in time_indicators:
                    words[idx - 3] = ""
                words[idx - 2] = ""
            else:
                hrOffset = 1
            if wordPrevPrev in time_indicators:
                words[idx - 2] = ""
            words[idx - 1] = ""
            used += 1
            hrAbs = -1
            minAbs = -1
        # parse 5:00 am, 12:00 p.m., etc
        elif word[0].isdigit():
            isTime = True
            strHH = ""
            strMM = ""
            remainder = ""
            if ':' in word:
                # parse colons
                # "3:00 in the morning"
                stage = 0
                length = len(word)
                for i in range(length):
                    if stage == 0:
                        if word[i].isdigit():
                            strHH += word[i]
                        elif word[i] == ":":
                            stage = 1
                        else:
                            stage = 2
                            i -= 1
                    elif stage == 1:
                        if word[i].isdigit():
                            strMM += word[i]
                        else:
                            stage = 2
                            i -= 1
                    elif stage == 2:
                        remainder = word[i:].replace(".", "")
                        break
                if remainder == "":
                    nextWord = wordNext.replace(".", "")
                    if nextWord == "am" or nextWord == "pm":
                        remainder = nextWord
                        used += 1
                    elif wordNext == "manha":
                        remainder = "am"
                        used += 1
                    elif wordNext == "tarde":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "noite":
                        if 0 < int(word[0]) < 6:
                            remainder = "am"
                        else:
                            remainder = "pm"
                        used += 1
                    elif wordNext in thises and wordNextNext == "manha":
                        remainder = "am"
                        used = 2
                    elif wordNext in thises and wordNextNext == "tarde":
                        remainder = "pm"
                        used = 2
                    elif wordNext in thises and wordNextNext == "noite":
                        remainder = "pm"
                        used = 2
                    else:
                        if timeQualifier != "":
                            military = True
                            if strHH <= 12 and \
                                    (timeQualifier == "manha" or
                                     timeQualifier == "tarde"):
                                strHH += 12

            else:
                # try to parse # s without colons
                # 5 hours, 10 minutes etc.
                length = len(word)
                strNum = ""
                remainder = ""
                for i in range(length):
                    if word[i].isdigit():
                        strNum += word[i]
                    else:
                        remainder += word[i]

                if remainder == "":
                    remainder = wordNext.replace(".", "").lstrip().rstrip()

                if (
                        remainder == "pm" or
                        wordNext == "pm" or
                        remainder == "p.m." or
                        wordNext == "p.m."):
                    strHH = strNum
                    remainder = "pm"
                    used = 1
                elif (
                        remainder == "am" or
                        wordNext == "am" or
                        remainder == "a.m." or
                        wordNext == "a.m."):
                    strHH = strNum
                    remainder = "am"
                    used = 1
                else:
                    if (wordNext == "pm" or
                            wordNext == "p.m." or
                            wordNext == "tarde"):
                        strHH = strNum
                        remainder = "pm"
                        used = 1
                    elif (wordNext == "am" or
                          wordNext == "a.m." or
                          wordNext == "manha"):
                        strHH = strNum
                        remainder = "am"
                        used = 1
                    elif (int(word) > 100 and
                            (
                                wordPrev == "o" or
                                wordPrev == "oh" or
                                wordPrev == "zero"
                            )):
                        # 0800 hours (pronounced oh-eight-hundred)
                        strHH = int(word) / 100
                        strMM = int(word) - strHH * 100
                        military = True
                        if wordNext == "hora":
                            used += 1
                    elif (
                            wordNext == "hora" and
                            word[0] != '0' and
                            (
                                int(word) < 100 and
                                int(word) > 2400
                            )):
                        # ignores military time
                        # "in 3 hours"
                        hrOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1

                    elif wordNext == "minuto":
                        # "in 10 minutes"
                        minOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif wordNext == "segundo":
                        # in 5 seconds
                        secOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif int(word) > 100:
                        strHH = int(word) / 100
                        strMM = int(word) - strHH * 100
                        military = True
                        if wordNext == "hora":
                            used += 1

                    elif wordNext == "" or (
                            wordNext == "em" and wordNextNext == "ponto"):
                        strHH = word
                        strMM = 00
                        if wordNext == "em" and wordNextNext == "ponto":
                            used += 2
                            if wordNextNextNext == "tarde":
                                remainder = "pm"
                                used += 1
                            elif wordNextNextNext == "manha":
                                remainder = "am"
                                used += 1
                            elif wordNextNextNext == "noite":
                                if 0 > strHH > 6:
                                    remainder = "am"
                                else:
                                    remainder = "pm"
                                used += 1

                    elif wordNext[0].isdigit():
                        strHH = word
                        strMM = wordNext
                        military = True
                        used += 1
                        if wordNextNext == "hora":
                            used += 1
                    else:
                        isTime = False

            strHH = int(strHH) if strHH else 0
            strMM = int(strMM) if strMM else 0
            strHH = strHH + 12 if (remainder == "pm" and
                                   0 < strHH < 12) else strHH
            strHH = strHH - 12 if (remainder == "am" and
                                   0 < strHH >= 12) else strHH
            if strHH > 24 or strMM > 59:
                isTime = False
                used = 0
            if isTime:
                hrAbs = strHH * 1
                minAbs = strMM * 1
                used += 1

        if used > 0:
            # removed parsed words from the sentence
            for i in range(used):
                words[idx + i] = ""

            if wordPrev == "em" or wordPrev == "ponto":
                words[words.index(wordPrev)] = ""

            if idx > 0 and wordPrev in time_indicators:
                words[idx - 1] = ""
            if idx > 1 and wordPrevPrev in time_indicators:
                words[idx - 2] = ""

            idx += used - 1
            found = True

    # check that we found a date
    if not date_found:
        return None

    if dayOffset is False:
        dayOffset = 0

    # perform date manipulation

    extractedDate = dateNow
    extractedDate = extractedDate.replace(microsecond=0,
                                          second=0,
                                          minute=0,
                                          hour=0)
    if datestr != "":
        en_months = ['january', 'february', 'march', 'april', 'may', 'june',
                     'july', 'august', 'september', 'october', 'november',
                     'december']
        en_monthsShort = ['jan', 'feb', 'mar', 'apr', 'may', 'june', 'july',
                          'aug',
                          'sept', 'oct', 'nov', 'dec']
        for idx, en_month in enumerate(en_months):
            datestr = datestr.replace(months[idx], en_month)
        for idx, en_month in enumerate(en_monthsShort):
            datestr = datestr.replace(monthsShort[idx], en_month)

        temp = datetime.strptime(datestr, "%B %d")
        if not hasYear:
            temp = temp.replace(year=extractedDate.year)
            if extractedDate < temp:
                extractedDate = extractedDate.replace(year=int(currentYear),
                                                      month=int(
                                                          temp.strftime(
                                                              "%m")),
                                                      day=int(temp.strftime(
                                                          "%d")))
            else:
                extractedDate = extractedDate.replace(
                    year=int(currentYear) + 1,
                    month=int(temp.strftime("%m")),
                    day=int(temp.strftime("%d")))
        else:
            extractedDate = extractedDate.replace(
                year=int(temp.strftime("%Y")),
                month=int(temp.strftime("%m")),
                day=int(temp.strftime("%d")))

    if timeStr != "":
        temp = datetime(timeStr)
        extractedDate = extractedDate.replace(hour=temp.strftime("%H"),
                                              minute=temp.strftime("%M"),
                                              second=temp.strftime("%S"))

    if yearOffset != 0:
        extractedDate = extractedDate + relativedelta(years=yearOffset)
    if monthOffset != 0:
        extractedDate = extractedDate + relativedelta(months=monthOffset)
    if dayOffset != 0:
        extractedDate = extractedDate + relativedelta(days=dayOffset)
    if hrAbs != -1 and minAbs != -1:

        extractedDate = extractedDate + relativedelta(hours=hrAbs,
                                                      minutes=minAbs)
        if (hrAbs != 0 or minAbs != 0) and datestr == "":
            if not daySpecified and dateNow > extractedDate:
                extractedDate = extractedDate + relativedelta(days=1)
    if hrOffset != 0:
        extractedDate = extractedDate + relativedelta(hours=hrOffset)
    if minOffset != 0:
        extractedDate = extractedDate + relativedelta(minutes=minOffset)
    if secOffset != 0:
        extractedDate = extractedDate + relativedelta(seconds=secOffset)

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())
    resultStr = pt_pruning(resultStr)
    return [extractedDate, resultStr]


def pt_pruning(text, symbols=True, accents=True, agressive=True):
    # agressive pt word pruning
    words = ["a", "o", "os", "as", "de", "dos", "das",
             "lhe", "lhes", "me", "e", "no", "nas", "na", "nos", "em", "para",
             "este",
             "esta", "deste", "desta", "neste", "nesta", "nesse",
             "nessa", "foi", "que"]
    if symbols:
        symbols = [".", ",", ";", ":", "!", "?", u"ï¿½", u"ï¿½"]
        for symbol in symbols:
            text = text.replace(symbol, "")
        text = text.replace("-", " ").replace("_", " ")
    if accents:
        accents = {"a": [u"á", u"à", u"ã", u"â"],
                   "e": [u"ê", u"è", u"é"],
                   "i": [u"í", u"ì"],
                   "o": [u"ò", u"ó"],
                   "u": [u"ú", u"ù"],
                   "c": [u"ç"]}
        for char in accents:
            for acc in accents[char]:
                text = text.replace(acc, char)
    if agressive:
        text_words = text.split(" ")
        for idx, word in enumerate(text_words):
            if word in words:
                text_words[idx] = ""
        text = " ".join(text_words)
        text = ' '.join(text.split())
    return text


def get_gender_pt(word, raw_string=""):
    word = word.rstrip("s")
    gender = False
    words = raw_string.split(" ")
    for idx, w in enumerate(words):
        if w == word and idx != 0:
            previous = words[idx - 1]
            gender = get_gender_pt(previous)
            break
    if not gender:
        if word[-1] == "a":
            gender = "f"
        if word[-1] == "o" or word[-1] == "e":
            gender = "m"
    return gender
