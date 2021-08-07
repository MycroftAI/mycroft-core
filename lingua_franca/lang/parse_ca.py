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
    Parse functions for Catalan (ca-ES)

    TODO: numbers greater than 999999
    TODO: date time ca
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
from lingua_franca.lang.parse_common import is_numeric, look_for_fractions
from lingua_franca.lang.common_data_ca import _NUMBERS_CA, \
    _FEMALE_DETERMINANTS_CA, _FEMALE_ENDINGS_CA, \
    _MALE_DETERMINANTS_CA, _MALE_ENDINGS_CA, _GENDERS_CA, \
    _TENS_CA, _AFTER_TENS_CA, _HUNDREDS_CA, _BEFORE_HUNDREDS_CA
from lingua_franca.internal import resolve_resource_file
from lingua_franca.lang.parse_common import Normalizer
import json
import re


def is_fractional_ca(input_str, short_scale=True):
    """
    This function takes the given text and checks if it is a fraction.

    Args:
        input_str (str): the string to check if fractional
        short_scale (bool): use short scale if True, long scale if False
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    if input_str.endswith('é', -1):
        input_str = input_str[:len(input_str) - 1] + "è"  # e.g. "cinqué -> cinquè"
    elif input_str.endswith('ena', -3):
        input_str = input_str[:len(input_str) - 3] + "è"  # e.g. "cinquena -> cinquè"
    elif input_str.endswith('ens', -3):
        input_str = input_str[:len(input_str) - 3] + "è"  # e.g. "cinquens -> cinquè"
    elif input_str.endswith('enes', -4):
        input_str = input_str[:len(input_str) - 4] + "è"  # e.g. "cinquenes -> cinquè"
    elif input_str.endswith('os', -2):
        input_str = input_str[:len(input_str) - 2]  # e.g. "terços -> terç"
    elif (input_str == 'terceres' or input_str == 'tercera'):
        input_str = "terç" # e.g. "tercer -> terç"
    elif (input_str == 'mitges' or input_str == 'mitja'):
        input_str = "mig" # e.g. "mitges -> mig"
    elif (input_str == 'meitat' or input_str == 'meitats'):
        input_str = "mig" # e.g. "mitges -> mig"
    elif input_str.endswith('a', -1):
        input_str = input_str[:len(input_str) - 1]  # e.g. "quarta -> quart"
    elif input_str.endswith('es', -2):
        input_str = input_str[:len(input_str) - 2]  # e.g. "quartes -> quartes"
    elif input_str.endswith('s', -1):
        input_str = input_str[:len(input_str) - 1]  # e.g. "quarts -> quart"


    aFrac = ["mig", "terç", "quart", "cinquè", "sisè", "sètè", "vuitè", "novè",
             "desè", "onzè", "dotzè", "tretzè", "catorzè", "quinzè", "setzè",
             "dissetè", "divuitè", "dinovè"]

    if input_str.lower() in aFrac:
        return 1.0 / (aFrac.index(input_str) + 2)
    if input_str == "vintè":
        return 1.0 / 20
    if input_str == "trentè":
        return 1.0 / 30
    if input_str == "centè":
        return 1.0 / 100
    if input_str == "milè":
        return 1.0 / 1000
    if (input_str == "vuitè" or input_str == "huitè"):
        return 1.0 / 8
    if (input_str == "divuitè" or input_str == "dihuitè"):
        return 1.0 / 18

    return False


def extract_number_ca(text, short_scale=True, ordinals=False):
    """
    This function prepares the given text for parsing by making
    numbers consistent, getting rid of contractions, etc.
    Args:
        text (str): the string to normalize
    Returns:
        (int) or (float): The value of extracted number

    """
    # TODO: short_scale and ordinals don't do anything here.
    # The parameters are present in the function signature for API compatibility
    # reasons.
    text = text.lower()
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
        if word in _NUMBERS_CA:
            val = _NUMBERS_CA[word]
        elif '-' in word:
            wordparts = word.split('-')
            # trenta-cinc > 35
            if len(wordparts) == 2 and (wordparts[0] in _TENS_CA and wordparts[1] in _AFTER_TENS_CA):
                val = _TENS_CA[wordparts[0]] + _AFTER_TENS_CA[wordparts[1]]
            # vint-i-dues > 22
            elif len(wordparts) == 3 and wordparts[1] == 'i' and (wordparts[0] in _TENS_CA and wordparts[2] in _AFTER_TENS_CA):
                val = _TENS_CA[wordparts[0]]+_AFTER_TENS_CA[wordparts[2]]
            # quatre-centes > 400
            elif len(wordparts) == 2 and (wordparts[0] in _BEFORE_HUNDREDS_CA and wordparts[1] in _HUNDREDS_CA):
                val = _BEFORE_HUNDREDS_CA[wordparts[0]]*100

        elif word.isdigit():  # doesn't work with decimals
            val = int(word)
        elif is_numeric(word):
            val = float(word)
        elif is_fractional_ca(word):
            if not result:
                result = 1
            result = result * is_fractional_ca(word)
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
            #TODO: caution, review use of "ens" word
            if next_word != "ens":
                result += val
            else:
                result = float(result) / float(val)

        if next_word is None:
            break

        # number word and fraction
        ands = ["i"]
        if next_word in ands:
            zeros = 0
            if result is None:
                count += 1
                continue
            newWords = aWords[count + 2:]
            newText = ""
            for word in newWords:
                newText += word + " "

            afterAndVal = extract_number_ca(newText[:-1])
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
                afterAndVal = extract_number_ca(newText[:-1])
                if afterAndVal:
                    if result is None:
                        result = 0
                    result += afterAndVal
                    break

        decimals = ["coma", "amb", "punt", ".", ","]
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
            afterDotVal = str(extract_number_ca(newText[:-1]))
            afterDotVal = zeros * "0" + afterDotVal
            result = float(str(result) + "." + afterDotVal)
            break
        count += 1

    # Return the $str with the number related words removed
    # (now empty strings, so strlen == 0)
    # aWords = [word for word in aWords if len(word) > 0]
    # text = ' '.join(aWords)
    if "." in str(result):
        integer, dec = str(result).split(".")
        # cast float to int
        if dec == "0":
            result = int(integer)

    return result or False


class CatalanNormalizer(Normalizer):
    with open(resolve_resource_file("text/ca-es/normalize.json")) as f:
        _default_config = json.load(f)

    @staticmethod
    def tokenize(utterance):
        # Split things like 12%
        utterance = re.sub(r"([0-9]+)([\%])", r"\1 \2", utterance)
        # Split things like #1
        utterance = re.sub(r"(\#)([0-9]+\b)", r"\1 \2", utterance)
        # Don't split things like amo-te
        #utterance = re.sub(r"([a-zA-Z]+)(-)([a-zA-Z]+\b)", r"\1 \3",
        #                   utterance)
        tokens = utterance.split()
        if tokens[-1] == '-':
            tokens = tokens[:-1]

        return tokens


def normalize_ca(text, remove_articles=True):
    """ CA string normalization """
    return CatalanNormalizer().normalize(text, remove_articles)


def extract_datetime_ca(text, anchorDate=None, default_time=None):
    def clean_string(s):
        # cleans the input string of unneeded punctuation and capitalization
        # among other things
        symbols = [".", ",", ";", "?", "!", "º", "ª"]
        hyphens = ["'", "_"]
        noise_words = ["el", "l", "els", "la", "les", "es", "sa", "ses",
                       "d", "de", "del", "dels"]
        # add final space
        s = s + " "

        s = s.lower()

        for word in symbols:
            s = s.replace(word, "")

        for word in hyphens:
            s = s.replace(word, " ")

        for word in noise_words:
            s = s.replace(" " + word + " ", " ")
            

        # handle synonims, plurals and equivalents, "demà ben d'hora" = "demà de matí"
        synonims = {"abans": ["abans-d"],
                    "vinent": ["que vé", "que ve", "que bé", "que be"],
                    "migdia": ["mig dia"],
                    "mitjanit": ["mitja nit"],
                    "matinada": ["matinades", "ben hora ben hora"],
                    "matí": ["matins", "dematí", "dematins", "ben hora"],
                    "tarda": ["tardes", "vesprada", "vesprades", "vespraes"],
                    "nit": ["nits", "vespre", "vespres", "horabaixa", "capvespre"],
                    "demà": ["endemà"],
                    "diàriament": ["diària", "diàries", "cada dia", "tots dies"],
                    "setmanalment": ["setmanal", "setmanals", "cada setmana", "totes setmanes"],
                    "quinzenalment": ["quinzenal", "quinzenals", "cada quinzena", "totes quinzenes"],
                    "mensualment": ["mensual", "mensuals", "cada mes", "tots mesos"],
                    "anualment": ["anual", "anuals", "cada any", "tots anys"],
                    "demàpassat": ["demà-passat", "demà passat", "passat demà", "despús-demà", "despús demà"],
                    "demàpassatpassat": ["demàpassat passat", "passat demàpassat",
                                         "demàpassat no altre", "demàpassat altre"],
                    "abansahir": ["abans ahir", "despús ahir", "despús-ahir"],
                    "abansabansahir": ["abans abansahir", "abansahir no altre", "abansahir altre",
                                             "abansahir no altre", "abansahir altre"],
                    "segon": ["segons"],
                    "minut": ["minuts"],
                    "quart": ["quarts"],
                    "hora": ["hores"],
                    "dia": ["dies"],
                    "setmana": ["setmanes"],
                    "quinzena": ["quinzenes"],
                    "mes": ["mesos"],
                    "any": ["anys"],
                    "tocat": ["tocats"],
                    "a": ["al", "als"]
                    }
        for syn in synonims:
            for word in synonims[syn]:
                s = s.replace(" " + word + " ", " " + syn + " ")

        # remove final space
        if s[-1] == " ":
            s = s[:-1]


        return s

    def date_found():
        return found or \
            (
                datestr != "" or timeStr != "" or
                yearOffset != 0 or monthOffset != 0 or
                dayOffset is True or hrOffset != 0 or
                hrAbs or minOffset != 0 or
                minAbs or secOffset != 0
            )

    if text == "" or not anchorDate:
        return None

    found = False
    daySpecified = False
    dayOffset = False
    monthOffset = 0
    yearOffset = 0
    dateNow = anchorDate
    today = dateNow.strftime("%w")
    currentYear = dateNow.strftime("%Y")
    fromFlag = False
    datestr = ""
    hasYear = False
    timeQualifier = ""

    words = clean_string(text).split(" ")
    timeQualifiersList = ['matí', 'tarda', 'nit']
    time_indicators = ["em", "a", "a les", "cap a", "vora", "després", "estas",
                       "no", "dia", "hora"]
    days = ['dilluns', 'dimarts', 'dimecres',
            'dijous', 'divendres', 'dissabte', 'diumenge']
    months = ['gener', 'febrer', 'març', 'abril', 'maig', 'juny',
              'juliol', 'agost', 'setembre', 'octubre', 'novembre',
              'desembre']
    monthsShort = ['gen', 'feb', 'març', 'abr', 'maig', 'juny', 'jul', 'ag',
                   'set', 'oct', 'nov', 'des']
    nexts = ["pròxim", "pròxima", "vinent"]
    suffix_nexts = ["següent", "després"]
    lasts = ["últim", "última", "darrer", "darrera", "passat", "passada"]
    suffix_lasts = ["passada", "passat", "anterior", "abans"]
    nxts = ["passat", "després", "segueix", "seguit", "seguida", "següent", "pròxim", "pròxima"]
    prevs = ["abans", "prèvia", "previamente", "anterior"]
    froms = ["partir", "dins", "des", "a",
             "després", "pròxima", "pròxim", "del", "de"]
    thises = ["aquest", "aquesta", "aqueix", "aqueixa", "este", "esta"]
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
        elif word == "avui" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "demà" and not fromFlag:
            dayOffset += 1
            used += 1
        elif word == "ahir" and not fromFlag:
            dayOffset -= 1
            used += 1
        # "before yesterday" and "before before yesterday"
        elif (word == "abansahir") and not fromFlag:
            dayOffset -= 2
            used += 1
        elif word == "abansabansahir" and not fromFlag:
            dayOffset -= 3
            used += 1
        # day after tomorrow and after after tomorrow
        elif word == "demàpassat" and not fromFlag:
            dayOffset += 2
            used = 1
        elif word == "demàpassatpassat" and not fromFlag:
            dayOffset += 3
            used = 1
        # parse 5 days, 10 weeks, last week, next week, week after
        elif word == "dia":
            if wordNext == "després" or wordNext == "abans":
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

        elif word == "setmana" and not fromFlag:
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
        elif word == "any" and not fromFlag:
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
                # 13 maig
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
                # maig 13
                datestr += " " + wordNext
                used += 1
                if wordNextNext and wordNextNext[0].isdigit():
                    datestr += " " + wordNextNext
                    used += 1
                    hasYear = True
                else:
                    hasYear = False

            elif wordPrevPrev and wordPrevPrev[0].isdigit():
                # 13 dia maig
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
                # maig dia 13
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
        validFollowups.append("avui")
        validFollowups.append("demà")
        validFollowups.append("ahir")
        validFollowups.append("abansahir")
        validFollowups.append("abansabansahir")
        validFollowups.append("demàpassat")
        validFollowups.append("ara")
        validFollowups.append("ja")
        validFollowups.append("abans")

        # TODO debug word "passat" that one is failing for some reason
        if word in froms and wordNext in validFollowups:

            if not (wordNext == "demà" and wordNext == "ahir") and not (
                    word == "passat" or word == "abans" or word == "em"):
                used = 2
                fromFlag = True
            if wordNext == "demà":
                dayOffset += 1
            elif wordNext == "ahir":
                dayOffset -= 1
            elif wordNext == "abansahir":
                dayOffset -= 2
            elif wordNext == "abansabansahir":
                dayOffset -= 3
            elif wordNext in days:
                d = days.index(wordNext)
                tmpOffset = (d + 1) - int(today)
                used = 2
                if wordNextNext == "dia":
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
                if wordNextNextNext == "dia":
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
    hrAbs = None
    minAbs = None
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
        if word == "migdia":
            hrAbs = 12
            used += 1
        elif word == "mijanit":
            hrAbs = 0
            used += 1
        elif word == "matí":
            if not hrAbs:
                hrAbs = 8
            used += 1
        elif word == "tarda":
            if not hrAbs:
                hrAbs = 15
            used += 1
        elif word == "mitja" and wordNext == "tarda":
            if not hrAbs:
                hrAbs = 17
            used += 2
        elif word == "mig" and wordNext == "matí":
            if not hrAbs:
                hrAbs = 10
            used += 2
        elif word == "vespre" or (word == "final" and wordNext == "tarda"):
            if not hrAbs:
                hrAbs = 19
            used += 2
        elif word == "final" and wordNext == "matí":
            if not hrAbs:
                hrAbs = 11
            used += 2
        elif word == "matinada":
            if not hrAbs:
                hrAbs = 4
            used += 1
        elif word == "nit":
            if not hrAbs:
                hrAbs = 22
            used += 1
        # parse half an hour, quarter hour
        elif word == "hora" and \
                (wordPrev in time_indicators or wordPrevPrev in
                 time_indicators):
            if wordPrev == "mitja":
                minOffset = 30
            elif wordPrev == "quart":
                minOffset = 15
            elif wordPrevPrev == "quart":
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
                    elif wordNext == "matí":
                        remainder = "am"
                        used += 1
                    elif (wordNext == "tarda" or wordNext == "vespre"):
                        remainder = "pm"
                        used += 1
                    elif wordNext == "nit":
                        if 0 < int(word[0]) < 6:
                            remainder = "am"
                        else:
                            remainder = "pm"
                        used += 1
                    elif wordNext in thises and wordNextNext == "matí":
                        remainder = "am"
                        used = 2
                    elif wordNext in thises and (wordNextNext == "tarda" or wordNextNext == "vespre"):
                        remainder = "pm"
                        used = 2
                    elif wordNext in thises and wordNextNext == "nit":
                        remainder = "pm"
                        used = 2
                    else:
                        if timeQualifier != "":
                            military = True
                            if strHH <= 12 and \
                                    (timeQualifier == "matí" or
                                     timeQualifier == "tarda"):
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
                            wordNext == "tarda" or
                            wordNext == "vespre"):
                        strHH = strNum
                        remainder = "pm"
                        used = 1
                    elif (wordNext == "am" or
                          wordNext == "a.m." or
                          wordNext == "matí"):
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

                    elif wordNext == "minut":
                        # "in 10 minutes"
                        minOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif wordNext == "segon":
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
                            wordNext == "en" and wordNextNext == "punt"):
                        strHH = word
                        strMM = 00
                        if wordNext == "en" and wordNextNext == "punt":
                            used += 2
                            if (wordNextNextNext == "tarda" or wordNextNextNext == "vespre"):
                                remainder = "pm"
                                used += 1
                            elif wordNextNextNext == "matí":
                                remainder = "am"
                                used += 1
                            elif wordNextNextNext == "nit":
                                if 0 > int(strHH) > 6:
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

            if wordPrev == "en" or wordPrev == "punt":
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
    if (hrAbs or 0) != -1 and (minAbs or 0) != -1:
        if hrAbs is None and minAbs is None and default_time:
            hrAbs = default_time.hour
            minAbs = default_time.minute
        extractedDate = extractedDate + relativedelta(hours=hrAbs or 0,
                                                      minutes=minAbs or 0)
        if (hrAbs or minAbs) and datestr == "":
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
    resultStr = _ca_pruning(resultStr)
    return [extractedDate, resultStr]


def _ca_pruning(text, symbols=True, accents=False, agressive=True):
    # agressive ca word pruning
    words = ["l", "la", "el", "els", "les", "de", "dels",
             "ell", "ells", "me", "és", "som", "al", "a", "dins", "per",
             "aquest", "aquesta", "això", "aixina", "en", "aquell", "aquella",
             "va", "vam", "vaig", "quin", "quina"]
    if symbols:
        symbols = [".", ",", ";", ":", "!", "?", "¡", "¿"]
        for symbol in symbols:
            text = text.replace(symbol, "")
        text = text.replace("'", " ").replace("_", " ")
    # accents=False
    if accents:
        accents = {"a": ["á", "à", "ã", "â"],
                   "e": ["ê", "è", "é"],
                   "i": ["í", "ï"],
                   "o": ["ò", "ó"],
                   "u": ["ú", "ü"],
                   "c": ["ç"],
                   "ll": ["l·l"],
                   "n": ["ñ"]}
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


def get_gender_ca(word, context=""):
    """ Guess the gender of a word

    Some languages assign genders to specific words.  This method will attempt
    to determine the gender, optionally using the provided context sentence.

    Args:
        word (str): The word to look up
        context (str, optional): String containing word, for context

    Returns:
        str: The code "m" (male), "f" (female) or "n" (neutral) for the gender,
             or None if unknown/or unused in the given language.
    """
    # parse gender taking context into account
    word = word.lower()
    words = context.lower().split(" ")
    for idx, w in enumerate(words):
        if w == word and idx != 0:
            # in Catalan usually the previous word (a determinant)
            # assigns gender to the next word
            previous = words[idx - 1].lower()
            if previous in _MALE_DETERMINANTS_CA:
                return "m"
            elif previous in _FEMALE_DETERMINANTS_CA:
                return "f"

    # get gender using only the individual word
    # see if this word has the gender defined
    if word in _GENDERS_CA:
        return _GENDERS_CA[word]
    singular = word.rstrip("s")
    if singular in _GENDERS_CA:
        return _GENDERS_CA[singular]
    # in Catalan the last vowel usually dosn't defines the gender of a word
    # the gender of the determinant takes precedence over this rule
    for end_str in _FEMALE_ENDINGS_CA:
        if word.endswith(end_str):
            return "f"
    for end_str in _MALE_ENDINGS_CA:
        if word.endswith(end_str):
            return "m"
    return None
