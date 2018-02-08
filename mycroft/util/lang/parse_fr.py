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
""" Parse functions for french (fr)

    Todo:
        * extractnumber_fr: ordinal numbers ("le cinquième")
        * extractnumber_fr: numbers greater than 999 999 ("cinq millions")
        * extract_datetime_fr: "quatrième lundi de janvier"
        * extract_datetime_fr: "5 heures moins le quart"
        * extract_datetime_fr: "troisième lundi de juillet"
        * get_gender_fr
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
from mycroft.util.lang.parse_common import is_numeric, look_for_fractions

# Undefined articles ["un", "une"] cannot be supressed,
# in French, "un cheval" means "a horse" or "one horse".
articles_fr = ["le", "la", "du", "de", "les", "des"]

numbers_fr = {
    "zéro": 0,
    "un": 1,
    "une": 1,
    "premier": 1,
    "première": 1,
    "deux": 2,
    "second": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "six": 6,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
    "onze": 11,
    "douze": 12,
    "treize": 13,
    "quatorze": 14,
    "quinze": 15,
    "seize": 16,
    "vingt": 20,
    "trente": 30,
    "quarante": 40,
    "cinquante": 50,
    "soixante": 60,
    "soixante-dix": 70,
    "septante": 70,
    "quatre-vingt": 80,
    "quatre-vingts": 80,
    "octante": 80,
    "huitante": 80,
    "quatre-vingt-dix": 90,
    "nonante": 90,
    "cent": 100,
    "cents": 100,
    "mille": 1000,
    "mil": 1000,
    "millier": 1000,
    "milliers": 1000,
    "million": 1000000,
    "millions": 1000000,
    "milliard": 1000000000,
    "milliards": 1000000000}


def number_parse_fr(words, i):
    """
    Takes in a list of words (strings without whitespace) and
    extracts a number that starts at the given index.
    Args:
        words (array): the list to extract a number from
        i (int): the index in words where to look for the number
    Returns:
        tuple with number, index of next word after the number.

        Returns None if no number was found.
    """
    def cte_fr(i, s):
        # Check if string s is equal to words[i].
        # If it is return tuple with s, index of next word.
        # If it is not return None.
        if i < len(words) and s == words[i]:
            return s, i + 1
        return None

    def number_word_fr(i, mi, ma):
        # Check if words[i] is a number in numbers_fr between mi and ma.
        # If it is return tuple with number, index of next word.
        # If it is not return None.
        if i < len(words):
            val = numbers_fr.get(words[i])
            # Numbers [1-16,20,30,40,50,60,70,80,90,100,1000]
            if val is not None:
                if val >= mi and val <= ma:
                    return val, i + 1
                else:
                    return None
            # The number may be hyphenated (numbers [17-99])
            splitWord = words[i].split('-')
            if len(splitWord) > 1:
                val1 = numbers_fr.get(splitWord[0])
                if val1:
                    i1 = 1
                    val2 = 0

                    # For [81-99], e.g. "quatre-vingt-deux"
                    if splitWord[0] == "quatre" and splitWord[1] == "vingt":
                        val1 = 80
                        i1 = 2

                    # For [21,31,41,51,61,71]
                    if splitWord[i1] == "et" and len(splitWord) > i1:
                        val2 = numbers_fr.get(splitWord[i1 + 1])
                    # For [77-79],[97-99] e.g. "soixante-dix-sept"
                    elif splitWord[i1] == "dix" and len(splitWord) > i1:
                        val2 = 10 + numbers_fr.get(splitWord[i1 + 1])
                    else:
                        val2 = numbers_fr.get(splitWord[i1])

                    if val2:
                        val = val1 + val2
                    else:
                        return None
                    if val and val >= min and val <= max:
                        return val, i + 1

        return None

    def number_1_99_fr(i):
        # Check if words[i] is a number between 1 and 99.
        # If it is return tuple with number, index of next word.
        # If it is not return None.

        # Is it a number between 1 and 16?
        result1 = number_word_fr(i, 1, 16)
        if result1:
            return result1

        # Is it a number between 10 and 99?
        result1 = number_word_fr(i, 10, 99)
        if result1:
            val1, i1 = result1
            result2 = cte_fr(i1, "et")
            # If the number is not hyphenated [21,31,41,51,61,71]
            if result2:
                i2 = result2[1]
                result3 = number_word_fr(i2, 1, 11)
                if result3:
                    val3, i3 = result3
                    return val1 + val3, i3
            return result1

        # It is not a number
        return None

    def number_1_999_fr(i):
        # Check if words[i] is a number between 1 and 999.
        # If it is return tuple with number, index of next word.
        # If it is not return None.

        # Is it 100 ?
        result1 = number_word_fr(i, 100, 100)

        # Is it [200,300,400,500,600,700,800,900]?
        if not result1:
            resultH1 = number_word_fr(i, 2, 9)
            if resultH1:
                valH1, iH1 = resultH1
                resultH2 = number_word_fr(iH1, 100, 100)
                if resultH2:
                    iH2 = resultH2[1]
                    result1 = valH1 * 100, iH2

        if result1:
            val1, i1 = result1
            result2 = number_1_99_fr(i1)
            if result2:
                val2, i2 = result2
                return val1 + val2, i2
            else:
                return result1

        # [1-99]
        result1 = number_1_99_fr(i)
        if result1:
            return result1

        return None

    def number_fr(i):
        # Check if words[i] is a number between 1 and 999,999.
        # If it is return tuple with number, index of next word.
        # If it is not return None.

        # check for zero
        result1 = number_word_fr(i, 0, 0)
        if result1:
            return result1

        # check for [1-999]
        result1 = number_1_999_fr(i)
        if result1:
            val1, i1 = result1
        else:
            val1 = 1
            i1 = i
        # check for 1000
        result2 = number_word_fr(i1, 1000, 1000)
        if result2:
            # it's [1000-999000]
            i2 = result2[1]
            # check again for [1-999]
            result3 = number_1_999_fr(i2)
            if result3:
                val3, i3 = result3
                return val1 * 1000 + val3, i3
            else:
                return val1 * 1000, i2
        elif result1:
            return result1
        return None

    return number_fr(i)


def extractnumber_fr(text):
    """Takes in a string and extracts a number.
    Args:
        text (str): the string to extract a number from
    Returns:
        (str): The number extracted or the original text.
    """
    # normalize text, remove articles
    text = normalize_fr(text, True)
    # split words by whitespace
    aWords = text.split()
    count = 0
    result = None
    add = False
    while count < len(aWords):
        val = None
        word = aWords[count]
        wordNext = None
        if count < (len(aWords) - 1):
            wordNext = aWords[count + 1]

        if word in ["et", "plus", "+"]:
            count += 1
            add = True
            continue

        # is current word a numeric number?
        if word.isdigit():
            val = int(word)
            count += 1
        elif is_numeric(word):
            val = float(word)
            count += 1
        # is current word the denominator of a fraction?
        elif isFractional_fr(word):
            val = isFractional_fr(word)
            count += 1

        # is current word the numerator of a fraction?
        if val and wordNext:
            valNext = isFractional_fr(wordNext)
            if valNext:
                val = float(val) * valNext
                count += 1

        if not val:
            count += 1
            # is current word a numeric fraction like "2/3"?
            aPieces = word.split('/')
            # if (len(aPieces) == 2 and is_numeric(aPieces[0])
            #   and is_numeric(aPieces[1])):
            if look_for_fractions(aPieces):
                val = float(aPieces[0]) / float(aPieces[1])

        # is current word followed by a decimal value?
        if wordNext == "virgule":
            zeros = 0
            newWords = aWords[count + 1:]
            # count the number of zeros after the decimal sign
            for word in newWords:
                if word == "zéro" or word == "0":
                    zeros += 1
                else:
                    break
            afterDotVal = None
            # extract the number after the zeros
            if newWords[zeros].isdigit():
                afterDotVal = newWords[zeros]
                countDot = count + zeros + 2
            # if a number was extracted (since comma is also a
            # punctuation sign)
            if afterDotVal:
                count = countDot
                if not val:
                    val = 0
                # add the zeros
                afterDotString = zeros * "0" + afterDotVal
                val = float(str(val) + "." + afterDotString)
        if val:
            if add:
                result += val
                add = False
            else:
                result = val

    # if result == False:
    if not result:
        return text

    return result


def extract_datetime_fr(string, currentDate=None):
    def clean_string(s):
        """
            cleans the input string of unneeded punctuation and capitalization
            among other things.
        """
        s = normalize_fr(s, True)
        wordList = s.split()
        for idx, word in enumerate(wordList):
            # remove comma and dot if it's not a number
            if word[-1] in [",", "."]:
                word = word[:-1]
            wordList[idx] = word

        return wordList

    def date_found():
        return found or \
            (
                datestr != "" or
                yearOffset != 0 or monthOffset != 0 or
                dayOffset is True or hrOffset != 0 or
                hrAbs != 0 or minOffset != 0 or
                minAbs != 0 or secOffset != 0
            )

    def is_ordinal(word):
        if word:
            ordinals = ["er", "ère", "ème", "e", "nd", "nde"]
            for ordinal in ordinals:
                if word[0].isdigit() and ordinal in word:
                    word = word.replace(ordinal, "")
                    return int(word)

        return None

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

    timeQualifiersList = ["matin", "après-midi", "soir"]
    markers = ["à", "dès", "autour", "vers", "environs", "dans",
               "ce", "cette", "après"]
    days = ["lundi", "mardi", "mercredi",
            "jeudi", "vendredi", "samedi", "dimanche"]
    months = ["janvier", "février", "mars", "avril", "mai", "juin",
              "juillet", "août", "septembre", "octobre", "novembre",
              "décembre"]
    monthsShort = ["jan", "fév", "mar", "avr", "mai", "juin", "juil", "aoû",
                   "sept", "oct", "nov", "déc"]
    # needed for format functions
    months_en = ['january', 'february', 'march', 'april', 'may', 'june',
                 'july', 'august', 'september', 'october', 'november',
                 'december']

    words = clean_string(string)

    for idx, word in enumerate(words):
        if word == "":
            continue
        wordPrevPrevPrev = words[idx - 3] if idx > 2 else ""
        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""

        start = idx
        used = 0
        # save timequalifier for later
        if word in timeQualifiersList:
            timeQualifier = word
        # parse aujourd'hui, demain, après-demain
        elif word == "aujourd'hui" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "demain" and not fromFlag:
            dayOffset = 1
            used += 1
        elif word == "après-demain" and not fromFlag:
            dayOffset = 2
            used += 1
        # parse 5 jours, 10 semaines, semaine dernière, semaine prochaine
        elif word in ["jour", "jours"]:
            if wordPrev.isdigit():
                dayOffset += int(wordPrev)
                start -= 1
                used = 2
            # "3e jour"
            elif is_ordinal(wordPrev) is not None:
                dayOffset += is_ordinal(wordPrev) - 1
                start -= 1
                used = 2
        elif word in ["semaine", "semaines"] and not fromFlag:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            elif wordNext in ["prochaine", "suivante"]:
                dayOffset = 7
                used = 2
            elif wordNext in ["dernière", "précédente"]:
                dayOffset = -7
                used = 2
        # parse 10 mois, mois prochain, mois dernier
        elif word == "mois" and not fromFlag:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordNext in ["prochain", "suivant"]:
                monthOffset = 1
                used = 2
            elif wordNext in ["dernier", "précédent"]:
                monthOffset = -1
                used = 2
        # parse 5 ans, an prochain, année dernière
        elif word in ["an", "ans", "année", "années"] and not fromFlag:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordNext in ["prochain", "prochaine", "suivant", "suivante"]:
                yearOffset = 1
                used = 2
            elif wordNext in ["dernier", "dernière", "précédent",
                              "précédente"]:
                yearOffset = -1
                used = 2
        # parse lundi, mardi etc., and lundi prochain, mardi dernier, etc.
        elif word in days and not fromFlag:
            d = days.index(word)
            dayOffset = (d + 1) - int(today)
            used = 1
            if dayOffset < 0:
                dayOffset += 7
            if wordNext in ["prochain", "suivant"]:
                dayOffset += 7
                used += 1
            elif wordNext in ["dernier", "précédent"]:
                dayOffset -= 7
                used += 1
        # parse 15 juillet, 15 juil
        elif word in months or word in monthsShort and not fromFlag:
            try:
                m = months.index(word)
            except ValueError:
                m = monthsShort.index(word)
            used += 1
            datestr = months_en[m]
            if wordPrev and (wordPrev[0].isdigit()):
                datestr += " " + wordPrev
                start -= 1
                used += 1
            else:
                datestr += " 1"
            if wordNext and wordNext[0].isdigit():
                datestr += " " + wordNext
                used += 1
                hasYear = True
            else:
                hasYear = False
        # parse 5 jours après demain, 10 semaines après jeudi prochain,
        # 2 mois après juillet
        validFollowups = days + months + monthsShort
        validFollowups.append("aujourd'hui")
        validFollowups.append("demain")
        validFollowups.append("prochain")
        validFollowups.append("prochaine")
        validFollowups.append("suivant")
        validFollowups.append("suivante")
        validFollowups.append("dernier")
        validFollowups.append("dernière")
        validFollowups.append("précédent")
        validFollowups.append("précédente")
        validFollowups.append("maintenant")
        if word in ["après", "depuis"] and wordNext in validFollowups:
            used = 2
            fromFlag = True
            if wordNext == "demain":
                dayOffset += 1
            elif wordNext in days:
                d = days.index(wordNext)
                tmpOffset = (d + 1) - int(today)
                used = 2
                if wordNextNext == "prochain":
                    tmpOffset += 7
                    used += 1
                elif wordNextNext == "dernier":
                    tmpOffset -= 7
                    used += 1
                elif tmpOffset < 0:
                    tmpOffset += 7
                dayOffset += tmpOffset
        if used > 0:
            if start - 1 > 0 and words[start - 1] in ["ce", "cette"]:
                start -= 1
                used += 1

            for i in range(0, used):
                words[i + start] = ""

            if start - 1 >= 0 and words[start - 1] in markers:
                words[start - 1] = ""
            found = True
            daySpecified = True

    # parse time
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
        # parse midi, minuit, matin, après-midi, soir
        used = 0
        if word == "midi":
            hrAbs = 12
            used += 1
        elif word == "minuit":
            hrAbs = 0
            used += 1
        elif word == "matin":
            if hrAbs == 0:
                hrAbs = 8
            used += 1
        elif word == "après-midi":
            if hrAbs == 0:
                hrAbs = 15
            used += 1
        elif word in ["soir", "soirée"]:
            if hrAbs == 0:
                hrAbs = 19
            used += 1
        # parse midi et quart, minuit et demi, midi 10, minuit moins 20
        if word in ["midi", "minuit"]:
            if wordNext.isdigit():
                minAbs = int(wordNext)
                used += 1
            elif wordNext == "et":
                if wordNextNext == "quart":
                    minAbs = 15
                    used += 2
                elif wordNextNext == "demi":
                    minAbs = 30
                    used += 2
            elif wordNext == "moins":
                if wordNextNext.isdigit():
                    minAbs = 60 - int(wordNextNext)
                    if hrAbs == 0:
                        hrAbs = 23
                    else:
                        hrAbs -= 1
                    used += 2
                if wordNextNext == "quart":
                    minAbs = 45
                    if hrAbs == 0:
                        hrAbs = 23
                    else:
                        hrAbs -= 1
                    used += 2
        # parse une demi-heure, un quart d'heure
        elif word == "demi-heure" or word == "heure" and \
                (wordPrevPrev in markers or wordPrevPrevPrev in markers):
            if word == "demi-heure":
                minOffset = 30
            elif wordPrev == "quart":
                minOffset = 15
            elif wordPrev == "quarts" and wordPrevPrev.isdigit():
                minOffset = int(wordPrevPrev) * 15
                words[idx - 2] = ""
            # else:
            #    hrOffset = 1
            if wordPrevPrevPrev in markers:
                words[idx - 3] = ""
            words[idx - 2] = ""
            words[idx - 1] = ""
            used += 1
            hrAbs = -1
            minAbs = -1
        # parse 5:00 du matin, 12:00, etc
        elif word[0].isdigit() and is_ordinal(word) is None:
            isTime = True
            strHH = ""
            strMM = ""
            remainder = ""
            if ":" in word or "h" in word:
                # parse hours on short format
                # "3:00 du matin", "4h14", "3h15min"
                stage = 0
                length = len(word)
                for i in range(length):
                    if stage == 0:
                        if word[i].isdigit():
                            strHH += word[i]
                            used = 1
                        elif word[i] in [":", "h"]:
                            stage = 1
                        else:
                            stage = 2
                            i -= 1
                    elif stage == 1:
                        if word[i].isdigit():
                            strMM += word[i]
                            used = 1
                        else:
                            stage = 2
                            if word[i:i+3] == "min":
                                i += 1
                    elif stage == 2:
                        break
                if remainder == "":
                    if wordNext == "matin":
                        remainder = "am"
                        used += 1
                    elif wordNext == "après-midi":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "soir":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "ce" and wordNextNext == "matin":
                        remainder = "am"
                        used = 2
                    elif wordNext in ["cet", "cette"] and \
                            wordNextNext == "après-midi":
                        remainder = "pm"
                        used = 2
                    elif wordNext == "ce" and wordNextNext == "soir":
                        remainder = "pm"
                        used = 2
                    elif wordNext == "cette" and wordNextNext == "nuit":
                        if int(strHH) > 8:
                            remainder = "pm"
                        else:
                            remainder = "am"
                        used += 2
            else:
                # try to parse time without colons
                # 5 hours, 10 minutes etc.
                length = len(word)
                strNum = ""
                remainder = ""
                for i in range(length):
                    if word[i].isdigit():
                        strNum += word[i]

                if (
                        wordNext in ["heures", "heure"] and word != "0" and
                        (
                            int(word) < 100 or
                            int(word) > 2400
                        )):
                    # "dans 3 heures", "à 3 heures"
                    if wordPrev in ["dans", "après"]:
                        hrOffset = int(word)
                        isTime = False
                    else:
                        strHH = strNum
                    used = 2
                    idxHr = idx + 2
                    # "dans 1 heure 40", "à 1 heure 40"
                    if idxHr < len(words):
                        # "3 heures 45"
                        if words[idxHr].isdigit():
                            if wordPrev in ["dans", "après"]:
                                minOffset = int(words[idxHr])
                            else:
                                strMM = int(words[idxHr])
                            used += 1
                            idxHr += 1
                        # "3 heures et quart", "4 heures et demi"
                        elif words[idxHr] == "et" and idxHr + 1 < len(words):
                            if words[idxHr + 1] == "quart":
                                if wordPrev in ["dans", "après"]:
                                    minOffset = 15
                                else:
                                    strMM = 15
                                used += 2
                                idxHr += 2
                            elif words[idxHr + 1] == "demi":
                                if wordPrev in ["dans", "après"]:
                                    minOffset = 30
                                else:
                                    strMM = 30
                                used += 2
                                idxHr += 2
                        # "5 heures moins 20", "6 heures moins le quart"
                        elif words[idxHr] == "moins" and \
                                idxHr + 1 < len(words):
                            if words[idxHr + 1].isdigit():
                                if wordPrev in ["dans", "après"]:
                                    hrOffset -= 1
                                    minOffset = 60 - int(words[idxHr + 1])
                                else:
                                    strHH = int(strHH) - 1
                                    strMM = 60 - int(words[idxHr + 1])
                                used += 2
                                idxHr += 2
                            elif words[idxHr + 1] == "quart":
                                if wordPrev in ["dans", "après"]:
                                    hrOffset -= 1
                                    minOffset = 45
                                else:
                                    strHH = int(strHH) - 1
                                    strMM = 45
                                used += 2
                                idxHr += 2
                        # remove word minutes if present
                        if idxHr < len(words) and \
                                words[idxHr] in ["minutes", "minute"]:
                            used += 1
                            idxHr += 1
                        # handle am/pm
                        if idxHr < len(words) and \
                                words[idxHr] in timeQualifiersList:
                            if words[idxHr] == "matin":
                                remainder = "am"
                            else:
                                remainder = "pm"
                            used += 1
                elif wordNext == "minutes":
                    # "dans 10 minutes"
                    if wordPrev in ["dans", "après"]:
                        minOffset = int(word)
                        isTime = False
                    else:
                        strMM = int(word)
                    used = 2
                    hrAbs = -1
                    minAbs = -1
                elif wordNext == "secondes":
                    # "dans 5 secondes"
                    secOffset = int(word)
                    isTime = False
                    used = 2
                    hrAbs = -1
                    minAbs = -1
                elif int(word) > 100:
                    # format militaire
                    strHH = int(word) / 100
                    strMM = int(word) - strHH * 100
                    used = 1
                    if wordNext == "heures":
                        used += 1

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
                # used += 1
        if used > 0:
            # removed parsed words from the sentence
            for i in range(used):
                words[idx + i] = ""

            if idx > 0 and wordPrev in markers:
                words[idx - 1] = ""
            if idx > 1 and wordPrevPrev in markers:
                words[idx - 2] = ""

            idx += used - 1
            found = True

    # check that we found a date
    if not date_found():
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
        if not hasYear:
            temp = datetime.strptime(datestr, "%B %d")
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
            temp = datetime.strptime(datestr, "%B %d %Y")
            extractedDate = extractedDate.replace(
                year=int(temp.strftime("%Y")),
                month=int(temp.strftime("%m")),
                day=int(temp.strftime("%d")))

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
        if words[idx] == "et" and words[idx - 1] == "" and words[
                idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())
    return [extractedDate, resultStr]


def isFractional_fr(input_str):
    """
    This function takes the given text and checks if it is a fraction.
    Args:
        input_str (str): the string to check if fractional
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction
    """
    input_str = input_str.lower()

    if input_str != "tiers" and input_str.endswith('s', -1):
        input_str = input_str[:len(input_str) - 1]  # e.g. "quarts"

    aFrac = ["entier", "demi", "tiers", "quart", "cinquième", "sixième",
             "septième", "huitième", "neuvième", "dixième", "onzième",
             "douzième", "treizième", "quatorzième", "quinzième", "seizième",
             "dix-septième", "dix-huitième", "dix-neuvième", "vingtième"]

    if input_str in aFrac:
        return 1.0 / (aFrac.index(input_str) + 1)
    if input_str == "trentième":
        return 1.0 / 30
    if input_str == "centième":
        return 1.0 / 100
    if input_str == "millième":
        return 1.0 / 1000

    return False


def normalize_fr(text, remove_articles):
    """ French string normalization """
    text = text.lower()
    words = text.split()  # this also removed extra spaces
    normalized = ""
    i = 0
    while i < len(words):
        # remove articles
        if remove_articles and words[i] in articles_fr:
            i += 1
            continue
        if remove_articles and words[i][:2] in ["l'", "d'"]:
            words[i] = words[i][2:]
        # remove useless punctuation signs
        if words[i] in ["?", "!", ";", "…"]:
            i += 1
            continue
        # Convert numbers into digits
        result = number_parse_fr(words, i)
        if result is not None:
            val, i = result
            normalized += " " + str(val)
            continue

        normalized += " " + words[i]
        i += 1

    return normalized[1:]  # strip the initial space
