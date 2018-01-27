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
    TODO: it_pruning

"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
from mycroft.util.lang.parse_common import is_numeric, look_for_fractions


# Undefined articles ["un", "una", "un'"] can not be supressed,
# in Italian, "un cavallo" means "a horse" or "one horse".
it_articles = ["il", "lo", "la", "i", "gli", "le"]

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
    "vent": 20,
    "trenta": 30,
    "trent": 30,
    "quaranta": 40,
    "quarant": 40,
    "cinquanta": 50,
    "cinquant": 50,
    "sessanta": 60,
    "sessant": 60,
    "settanta": 70,
    "settant": 70,
    "ottanta": 80,
    "ottant": 80,
    "novanta": 90,
    "novant": 90,
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


def extractnumber_long_it(word):
    """
    Questa funzione converte un numero testuale lungo es.
    ventisette -> 27
    quarantuno -> 41
    nell'equivalente valore intero
     args:
         text (str): la stringa da normalizzare
    Ritorna:
         (int) : il valore del numero estratto usando tutta la parola
         Falso : se la parola non è un numero es."qualcuno"
    """
    result = False
    value = False

    for number in it_numbers.keys():  # ciclo unità
        if word.endswith(number):
            result = True
            value = it_numbers[number]
            word = word[0: len(word) - len(number)]
            break

    if result:  # tolte le unità, dovrebbe rimanere una stringa nota
        if word in it_numbers:
            value += it_numbers[word]
        else:
            value = False  # non è un numero es. qualcuno

    return value


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

        if not val:
            # cerca numero composto come ventuno ventitre centoventi"
            val = extractnumber_long_it(word)

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
    # Convert numbers into digits, e.g. "quarantadue" -> "42"
    normalized = ""
    i = 0

    while i < len(words):
        word = words[i]
        # remove articles
        # Italian requires the article to define the gender
        if remove_articles and word in it_articles:
            i += 1
            continue

        if word in it_numbers:
            word = str(it_numbers[word])

        val = extractnumber_long_it(word)

        if val:
            word = str(val)

        normalized += " " + word
        i += 1
    # indefinite articles in it-it can not be removed

    return normalized[1:]


def extract_datetime_it(string, currentDate=None):
    def clean_string(s):
        """
            cleans the input string of unneeded punctuation and capitalization
            among other things.
            Normalize italian plurals
        """
        symbols = [".", ",", ";", "?", "!", u"º", u"ª", u"°"]

        for word in symbols:
            s = s.replace(word, "")

        s = s.lower().replace(
            u"á",
            "a").replace(
            u"à",
            "a").replace(
            u"è",
            "e'").replace(
            u"é",
            "e'").replace(
            u"ì",
            "i").replace(
            u"ù",
            "u").replace(
            u"ò",
            "o").replace(
            "-",
            " ").replace(
            "_",
            "")

        noise_words = ["tra", "la", "del", "al", "il", "di",
                       "le", "per", "alle", "alla", "dai", "delle",
                       "a", "e'", "era", "questa", "questo", "e"]

        for word in noise_words:
            s = s.replace(" " + word + " ", " ")

        # normalizza plurali per semplificare analisi
        s = s.replace(
            "secondi",
            "secondo").replace(
            "minuti",
            "minuto").replace(
            "ore",
            "ora").replace(
            "giorni",
            "giorno").replace(
            "settimane",
            "settimana").replace(
            "mesi",
            "mese").replace(
            "anni",
            "anno").replace(
            "mattino",
            "mattina").replace(
            "prossima",
            "prossimo").replace(
            "questa",
            "questo").replace(
            "quarti",
            "quarto")

        wordList = s.split()
        # print(wordList)  # debug only

        return wordList

    def date_found():
        return found or \
            (
                datestr != "" or timeStr != "" or
                yearOffset != 0 or monthOffset != 0 or
                dayOffset is True or hrOffset != 0 or
                hrAbs != 0 or minOffset != 0 or
                minAbs != 0 or secOffset != 0
            )

    if string == "":
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

    timeQualifiersList = ['mattina', 'pomeriggio', 'sera']
    markers = ['alle', 'in', 'questo',  'per', 'di']
    days = ['lunedi', 'martedi', 'mercoledi',
            'giovedi', 'venerdi', 'sabato', 'domenica']
    months = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
              'luglio', 'agosto', 'settembre', 'ottobre', 'novembre',
              'dicembre']
    monthsShort = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago',
                   'set', 'ott', 'nov', 'dic']

    words = clean_string(string)

    for idx, word in enumerate(words):
        if word == "":
            continue
        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""
        # wordNextNextNext = words[idx + 3] if idx + 3 < len(words) else ""
        # possono esistere casi dove servano tre parole di profondità ?
        start = idx
        used = 0
        # save timequalifier for later
        if word in timeQualifiersList:
            timeQualifier = word
            # parse today, tomorrow, day after tomorrow
        elif word == "oggi" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "domani" and not fromFlag:
            dayOffset = 1
            used += 1
        elif word == "ieri" and not fromFlag:
            dayOffset -= 1
            used += 1
        elif word == "dopodomani" and not fromFlag:  # after tomorrow
            dayOffset += 2
            used += 1
        elif word == "dopo" and wordNext == "domani" and \
                not fromFlag:
            dayOffset += 1
            used += 2
        elif word == "giorno":
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev)
                start -= 1
                used = 2
                if wordNext == "dopo" and wordNextNext == "domani":
                    dayOffset += 1
                    used += 2
        elif word == "settimana" and not fromFlag:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            elif wordPrev == "prossimo":
                dayOffset = 7
                start -= 1
                used = 2
            elif wordPrev == "passato":
                dayOffset = -7
                start -= 1
                used = 2
                # parse 10 months, next month, last month
        elif word == "mese" and not fromFlag:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "prossimo":
                monthOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "passato":
                monthOffset = -1
                start -= 1
                used = 2
                # parse 5 years, next year, last year
        elif word == "anno" and not fromFlag:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "prossimo":
                yearOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "passato":
                yearOffset = -1
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
            if wordPrev == "prossimo":
                dayOffset += 7
                used += 1
                start -= 1
            elif wordPrev == "passato":
                dayOffset -= 7
                used += 1
                start -= 1
            if wordNext == "prossimo":
                # dayOffset += 7
                used += 1
            elif wordNext == "passato":
                # dayOffset -= 7
                used += 1
                # parse 15 of July, June 20th, Feb 18, 19 of February
        elif word in months or word in monthsShort and not fromFlag:
            try:
                m = months.index(word)
            except ValueError:
                m = monthsShort.index(word)
            used += 1
            datestr = months[m]
            if wordPrev and (wordPrev[0].isdigit()):
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
                datestr += " " + wordNext
                used += 1
                if wordNextNext and wordNextNext[0].isdigit():
                    datestr += " " + wordNextNext
                    used += 1
                    hasYear = True
                else:
                    hasYear = False
        # parse 5 days from tomorrow, 10 weeks from next thursday,
        # 2 months from July
        validFollowups = days + months + monthsShort
        validFollowups.append("oggi")
        validFollowups.append("domani")
        validFollowups.append("prossimo")
        validFollowups.append("passato")
        validFollowups.append("ora")
        if (word == "da" or word == "dopo") and wordNext in validFollowups:
            used = 2
            fromFlag = True
            if wordNext == "domani":
                dayOffset += 1
            elif wordNext in days:
                d = days.index(wordNext)
                tmpOffset = (d + 1) - int(today)
                used = 2
                if tmpOffset < 0:
                    tmpOffset += 7
                dayOffset += tmpOffset
            elif wordNextNext and wordNextNext in days:
                d = days.index(wordNextNext)
                tmpOffset = (d + 1) - int(today)
                used = 3
                if wordNext == "prossimo":
                    tmpOffset += 7
                    used += 2  # era 1
                    start -= 1
                elif wordNext == "passato":
                    tmpOffset -= 7
                    used += 1
                    start -= 1
                dayOffset += tmpOffset
        if used > 0:
            if start - 1 > 0 and words[start - 1] == "questo":
                start -= 1
                used += 1

            for i in range(0, used):
                words[i + start] = ""

            if start - 1 >= 0 and words[start - 1] in markers:
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

    for idx, word in enumerate(words):
        if word == "":
            continue

        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""
        # wordNextNextNext = words[idx + 3] if idx + 3 < len(words) else ""
        # TODO verfica se esistono casi dove serva profindita 3 x analisi
        # parse noon, midnight, morning, afternoon, evening
        used = 0
        if word == "mezzogiorno":
            hrAbs = 12
            used += 1
        elif word == "mezzanotte":
            hrAbs = 24
            used += 1
        if word == "mezzo" and wordNext == "giorno":  # if stt splits the word
            hrAbs = 12
            used += 2
        elif word == "mezza"and wordNext == "notte":  # if stt splits the word
            hrAbs = 24
            used += 2
        elif word == "mattina":
            if hrAbs == 0:
                hrAbs = 8
            used += 1
            if wordNext and wordNext[0].isdigit():  # mattina alle 5
                hrAbs = int(wordNext)
                used += 1
        elif word == "pomeriggio":
            if hrAbs == 0:
                hrAbs = 15
            used += 1
            if wordNext and wordNext[0].isdigit():  # pomeriggio alle 5
                hrAbs = int(wordNext)
                used += 1
                if hrAbs < 12:
                    hrAbs += 12
        elif word == "sera":
            if hrAbs == 0:
                hrAbs = 19
            used += 1
            if wordNext and wordNext[0].isdigit():  # sera alle 8
                hrAbs = int(wordNext)
                used += 1
                if hrAbs < 12:
                    hrAbs += 12

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
                    elif nextWord == "sera":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "mattina":
                        remainder = "am"
                        used += 1
                    elif wordNext == "pomeriggio":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "notte":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "di" and wordNextNext == "notte":
                        if strHH > 5:
                            remainder = "pm"
                        else:
                            remainder = "am"
                        used += 2
                    else:
                        if timeQualifier != "":
                            if strHH <= 12 and \
                                    (timeQualifier == "sera" or
                                     timeQualifier == "pomeriggio"):
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
                    if wordNext == "pm" or wordNext == "p.m.":
                        strHH = strNum
                        remainder = "pm"
                        used = 1
                    elif wordNext == "am" or wordNext == "a.m.":
                        strHH = strNum
                        remainder = "am"
                        used = 1
                    elif (
                            int(word) > 100 and
                            (
                                wordPrev == "o" or
                                wordPrev == "oh"
                            )):
                        # 0800 hours (pronounced oh-eight-hundred)
                        strHH = int(word) / 100
                        strMM = int(word) - strHH * 100
                        if wordNext == "ora":
                            used += 1

                    elif (
                            wordNext == "ora" and
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
                    elif wordNext == "mattina":
                        # " 11 del mattina"  -> del viene rimosso
                        hh = int(word)
                        used = 2
                        isTime = False
                        hrAbs = hh
                        minAbs = 00
                    elif wordNext == "pomeriggio":
                        # " 2 del pomeriggio"  -> del viene rimosso
                        hh = int(word)
                        if hh < 12:
                            hh += 12
                        used = 2
                        isTime = False
                        hrAbs = hh
                        minAbs = 00
                    elif wordNext == "sera":
                        # "alle 8 di sera"  -> alle viene rimosso
                        hh = int(word)
                        if hh < 12:
                            hh += 12
                        used = 2
                        isTime = False
                        hrAbs = hh
                        minAbs = 00
                    # parse half an hour : undici e mezza
                    elif wordNext and wordNext == "mezza":
                        hrAbs = int(word)
                        minAbs = 30
                        used = 2
                        isTime = False
                    # parse 1 quarter hour 3 quarters : dieci e tre quarti
                    elif word and wordNext and \
                            wordNext == "quarto" and word[0].isdigit():
                        minAbs = 15 * int(word)
                        used = 2
                        if minAbs > 45:  # elimina eventuali errori
                            minAbs = 0
                            used -= 2
                        isTime = False
                    elif wordNext == "minuto":
                        # "in 10 minutes"
                        minOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif wordNext == "secondo":
                        # in 5 seconds
                        secOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif int(word) > 100:
                        strHH = int(word) / 100
                        strMM = int(word) - strHH * 100
                        if wordNext == "ora":
                            used += 1
                    elif wordNext and wordNext[0].isdigit():
                        strHH = word
                        strMM = wordNext
                        used += 1
                        if wordNextNext == "ora":
                            used += 1
                    elif wordNext == "in" and wordNextNext == "punto":
                        strHH = word
                        strMM = 00
                        used += 2

                    else:
                        isTime = False

            strHH = int(strHH) if strHH else 0
            strMM = int(strMM) if strMM else 0
            strHH = strHH + 12 if remainder == "pm" and strHH < 12 else strHH
            strHH = strHH - 12 if remainder == "am" and strHH >= 12 else strHH
            if strHH > 24 or strMM > 59:
                isTime = False
                used = 0
            if isTime:
                hrAbs = strHH * 1
                minAbs = strMM * 1
                used += 1

            if hrAbs <= 12 and (timeQualifier == "sera" or
                                timeQualifier == "pomeriggio"):
                hrAbs += 12

        if used > 0:
            # removed parsed words from the sentence
            for i in range(used):
                words[idx + i] = ""

            if wordPrev == "o" or wordPrev == "oh":
                words[words.index(wordPrev)] = ""

            if wordPrev == "presto":
                hrOffset = -1
                words[idx - 1] = ""
                idx -= 1
            elif wordPrev == "tardi":
                hrOffset = 1
                words[idx - 1] = ""
                idx -= 1
            if idx > 0 and wordPrev in markers:
                words[idx - 1] = ""
            if idx > 1 and wordPrevPrev in markers:
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
    for idx, word in enumerate(words):
        if words[idx] == "e" and words[idx - 1] == "" and words[
                idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())
    return [extractedDate, resultStr]


def get_gender_it(word, raw_string=""):
    """
    Questa potrebbe non essere utile.
    In italiano per definire il genere è necessario
    analizzare l'articolo che la precede e non la lettera
    con cui finisce la parola, ma sono presenti funzioni per
    la rimozione degli articoli dalla frase per semplificarne
    l'analisi

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
