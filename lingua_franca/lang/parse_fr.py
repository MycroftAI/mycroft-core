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
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from lingua_franca.lang.parse_common import is_numeric, look_for_fractions, \
    extract_numbers_generic, Normalizer
from lingua_franca.lang.format_fr import pronounce_number_fr
from lingua_franca.lang.common_data_fr import _ARTICLES_FR, _NUMBERS_FR, \
    _ORDINAL_ENDINGS_FR

def extract_duration_fr(text):
    """
    Convert an french phrase into a number of seconds
    Convert things like:
        "10 minutes"
        "3 jours 8 heures 10 minutes und 49 secondes"
    into an int, representing the total number of seconds.
    The words used in the duration will be consumed, and
    the remainder returned.
    As an example, "set a timer for 5 minutes" would return
    (300, "set a timer for").
    Args:
        text (str): string containing a duration
    Returns:
        (timedelta, str):
                    A tuple containing the duration and the remaining text
                    not consumed in the parsing. The first value will
                    be None if no duration is found. The text returned
                    will have whitespace stripped from the ends.
    """
    if not text:
        return None

    text = normalize_fr(text)

    time_units = {
        'microseconds': 'microsecondes',
        'milliseconds': 'millisecondes',
        'seconds': 'secondes',
        'minutes': 'minutes',
        'hours': 'heures',
        'days': 'jours',
        'weeks': 'semaines'
    }

    pattern = r"(?P<value>\d+(?:\.?\d+)?)(?:\s+|\-){unit}[s]?(\s+|,|$)"

    for (unit_en, unit_fr) in time_units.items():
        unit_pattern = pattern.format(unit=unit_fr[:-1])  # remove 's' from unit
        time_units[unit_en] = 0

        def repl(match):
            time_units[unit_en] += float(match.group(1))
            return ''
        text = re.sub(unit_pattern, repl, text)

    text = text.strip()
    duration = timedelta(**time_units) if any(time_units.values()) else None

    return (duration, text)

def _number_parse_fr(words, i):
    """ Parses a list of words to find a number
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
        # Check if words[i] is a number in _NUMBERS_FR between mi and ma.
        # If it is return tuple with number, index of next word.
        # If it is not return None.
        if i < len(words):
            val = _NUMBERS_FR.get(words[i])
            # Numbers [1-16,20,30,40,50,60,70,80,90,100,1000]
            if val is not None:
                if val >= mi and val <= ma:
                    return val, i + 1
                else:
                    return None
            # The number may be hyphenated (numbers [17-999])
            splitWord = words[i].split('-')
            if len(splitWord) > 1:
                val1 = _NUMBERS_FR.get(splitWord[0])
                if val1:
                    i1 = 0
                    val2 = 0
                    val3 = 0
                    if val1 < 10 and splitWord[1] == "cents":
                        val1 = val1 * 100
                        i1 = 2

                    # For [81-99], e.g. "quatre-vingt-deux"
                    if len(splitWord) > i1 and splitWord[0] == "quatre" and \
                            splitWord[1] == "vingt":
                        val1 = 80
                        i1 += 2

                    # We still found a number
                    if i1 == 0:
                        i1 = 1

                    if len(splitWord) > i1:
                        # For [21,31,41,51,61,71]
                        if len(splitWord) > i1 + 1 and splitWord[i1] == "et":
                            val2 = _NUMBERS_FR.get(splitWord[i1 + 1])
                            if val2 is not None:
                                i1 += 2
                        # For [77-79],[97-99] e.g. "soixante-dix-sept"
                        elif splitWord[i1] == "dix" and \
                                len(splitWord) > i1 + 1:
                            val2 = _NUMBERS_FR.get(splitWord[i1 + 1])
                            if val2 is not None:
                                val2 += 10
                                i1 += 2
                        else:
                            val2 = _NUMBERS_FR.get(splitWord[i1])
                            if val2 is not None:
                                i1 += 1
                                if len(splitWord) > i1:
                                    val3 = _NUMBERS_FR.get(splitWord[i1])
                                    if val3 is not None:
                                        i1 += 1

                        if val2:
                            if val3:
                                val = val1 + val2 + val3
                            else:
                                val = val1 + val2
                        else:
                            return None
                    if i1 == len(splitWord) and val and ma >= val >= mi:
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
        result = number_word_fr(i, 100, 100)

        # Is it [200,300,400,500,600,700,800,900]?
        if not result:
            resultH1 = number_word_fr(i, 2, 9)
            if resultH1:
                valH1, iH1 = resultH1
                resultH2 = number_word_fr(iH1, 100, 100)
                if resultH2:
                    iH2 = resultH2[1]
                    result = valH1 * 100, iH2

        if result:
            val1, i1 = result
            result2 = number_1_99_fr(i1)
            if result2:
                val2, i2 = result2
                return val1 + val2, i2
            else:
                return result

        # Is it hyphenated? [101-999]
        result = number_word_fr(i, 101, 999)
        if result:
            return result

        # [1-99]
        result = number_1_99_fr(i)
        if result:
            return result

        return None

    def number_1_999999_fr(i):
        """ Find a number in a list of words
        Checks if words[i] is a number between 1 and 999,999.

        Args:
            i (int): the index in words where to look for the number
        Returns:
            tuple with number, index of next word after the number.

            Returns None if no number was found.
        """

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

    return number_1_999999_fr(i)


def _get_ordinal_fr(word):
    """ Get the ordinal number
    Takes in a word (string without whitespace) and
    extracts the ordinal number.
    Args:
        word (string): the word to extract the number from
    Returns:
        number (int)

        Returns None if no ordinal number was found.
    """
    if word:
        for ordinal in _ORDINAL_ENDINGS_FR:
            if word[0].isdigit() and ordinal in word:
                result = word.replace(ordinal, "")
                if result.isdigit():
                    return int(result)

    return None


def _number_ordinal_fr(words, i):
    """ Find an ordinal number in a list of words
    Takes in a list of words (strings without whitespace) and
    extracts an ordinal number that starts at the given index.
    Args:
        words (array): the list to extract a number from
        i (int): the index in words where to look for the ordinal number
    Returns:
        tuple with ordinal number (str),
        index of next word after the number (int).

        Returns None if no ordinal number was found.
    """
    val1 = None
    strOrd = ""
    # it's already a digit, normalize to "1er" or "5e"
    val1 = _get_ordinal_fr(words[i])
    if val1 is not None:
        if val1 == 1:
            strOrd = "1er"
        else:
            strOrd = str(val1) + "e"
        return strOrd, i + 1

    # if it's a big number the beginning should be detected as a number
    result = _number_parse_fr(words, i)
    if result:
        val1, i = result
    else:
        val1 = 0

    if i < len(words):
        word = words[i]
        if word in ["premier", "première"]:
            strOrd = "1er"
        elif word == "second":
            strOrd = "2e"
        elif word.endswith("ième"):
            val2 = None
            word = word[:-4]
            # centième
            if word == "cent":
                if val1:
                    strOrd = str(val1 * 100) + "e"
                else:
                    strOrd = "100e"
            # millième
            elif word == "mill":
                if val1:
                    strOrd = str(val1 * 1000) + "e"
                else:
                    strOrd = "1000e"
            else:
                # "cinquième", "trente-cinquième"
                if word.endswith("cinqu"):
                    word = word[:-1]
                # "neuvième", "dix-neuvième"
                elif word.endswith("neuv"):
                    word = word[:-1] + "f"
                result = _number_parse_fr([word], 0)
                if not result:
                    # "trentième", "douzième"
                    word = word + "e"
                    result = _number_parse_fr([word], 0)
                if result:
                    val2, i = result
                if val2 is not None:
                    strOrd = str(val1 + val2) + "e"
        if strOrd:
            return strOrd, i + 1

    return None


def extract_number_fr(text, short_scale=True, ordinals=False):
    """Takes in a string and extracts a number.
    Args:
        text (str): the string to extract a number from
    Returns:
        (str): The number extracted or the original text.
    """
    # TODO: short_scale and ordinals don't do anything here.
    # The parameters are present in the function signature for API compatibility
    # reasons.
    # normalize text, keep articles for ordinals versus fractionals
    text = normalize_fr(text, False)
    # split words by whitespace
    aWords = text.split()
    count = 0
    result = None
    add = False
    while count < len(aWords):
        val = None
        word = aWords[count]
        wordNext = ""
        wordPrev = ""
        if count < (len(aWords) - 1):
            wordNext = aWords[count + 1]
        if count > 0:
            wordPrev = aWords[count - 1]

        if word in _ARTICLES_FR:
            count += 1
            continue
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
        elif wordPrev in _ARTICLES_FR and _get_ordinal_fr(word):
            val = _get_ordinal_fr(word)
            count += 1
        # is current word the denominator of a fraction?
        elif is_fractional_fr(word):
            val = is_fractional_fr(word)
            count += 1

        # is current word the numerator of a fraction?
        if val and wordNext:
            valNext = is_fractional_fr(wordNext)
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

    return result or False


def extract_datetime_fr(text, anchorDate=None, default_time=None):
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
                yearOffset != 0 or monthOffset != 0 or dayOffset or
                (isTime and (hrAbs or minAbs)) or
                hrOffset != 0 or minOffset != 0 or secOffset != 0
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

    timeQualifiersList = ["matin", "après-midi", "soir", "nuit"]
    words_in = ["dans", "après"]
    markers = ["à", "dès", "autour", "vers", "environs", "ce",
               "cette"] + words_in
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

    words = clean_string(text)

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
            used = 1
            if wordPrev in ["ce", "cet", "cette"]:
                used = 2
                start -= 1
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
            elif _get_ordinal_fr(wordPrev) is not None:
                dayOffset += _get_ordinal_fr(wordPrev) - 1
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
    hrAbs = None
    minAbs = None
    ampm = ""
    isTime = False

    for idx, word in enumerate(words):
        if word == "":
            continue

        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""
        used = 0
        start = idx

        # parse midi et quart, minuit et demi, midi 10, minuit moins 20
        if word in ["midi", "minuit"]:
            isTime = True
            if word == "midi":
                hrAbs = 12
                used += 1
            elif word == "minuit":
                hrAbs = 0
                used += 1
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
                    if not hrAbs:
                        hrAbs = 23
                    else:
                        hrAbs -= 1
                    used += 2
                if wordNextNext == "quart":
                    minAbs = 45
                    if not hrAbs:
                        hrAbs = 23
                    else:
                        hrAbs -= 1
                    used += 2
        # parse une demi-heure, un quart d'heure
        elif word == "demi-heure" or word == "heure" and \
                (wordPrevPrev in markers or wordPrevPrevPrev in markers):
            used = 1
            isTime = True
            if word == "demi-heure":
                minOffset = 30
            elif wordPrev == "quart":
                minOffset = 15
                used += 1
                start -= 1
            elif wordPrev == "quarts" and wordPrevPrev.isdigit():
                minOffset = int(wordPrevPrev) * 15
                used += 1
                start -= 1
            if wordPrev.isdigit() or wordPrevPrev.isdigit():
                start -= 1
                used += 1
        # parse 5:00 du matin, 12:00, etc
        elif word[0].isdigit() and _get_ordinal_fr(word) is None:
            isTime = True
            if ":" in word or "h" in word or "min" in word:
                # parse hours on short format
                # "3:00 du matin", "4h14", "3h15min"
                strHH = ""
                strMM = ""
                stage = 0
                length = len(word)
                for i in range(length):
                    if stage == 0:
                        if word[i].isdigit():
                            strHH += word[i]
                            used = 1
                        elif word[i] in [":", "h", "m"]:
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
                            if word[i:i + 3] == "min":
                                i += 1
                    elif stage == 2:
                        break
                if wordPrev in words_in:
                    hrOffset = int(strHH) if strHH else 0
                    minOffset = int(strMM) if strMM else 0
                else:
                    hrAbs = int(strHH) if strHH else 0
                    minAbs = int(strMM) if strMM else 0
            else:
                # try to parse time without colons
                # 5 hours, 10 minutes etc.
                length = len(word)
                ampm = ""
                if (
                        word.isdigit() and
                        wordNext in ["heures", "heure"] and word != "0" and
                        (
                            int(word) < 100 or
                            int(word) > 2400
                        )):
                    # "dans 3 heures", "à 3 heures"
                    if wordPrev in words_in:
                        hrOffset = int(word)
                    else:
                        hrAbs = int(word)
                    used = 2
                    idxHr = idx + 2
                    # "dans 1 heure 40", "à 1 heure 40"
                    if idxHr < len(words):
                        # "3 heures 45"
                        if words[idxHr].isdigit():
                            if wordPrev in words_in:
                                minOffset = int(words[idxHr])
                            else:
                                minAbs = int(words[idxHr])
                            used += 1
                            idxHr += 1
                        # "3 heures et quart", "4 heures et demi"
                        elif words[idxHr] == "et" and idxHr + 1 < len(words):
                            if words[idxHr + 1] == "quart":
                                if wordPrev in words_in:
                                    minOffset = 15
                                else:
                                    minAbs = 15
                                used += 2
                                idxHr += 2
                            elif words[idxHr + 1] == "demi":
                                if wordPrev in words_in:
                                    minOffset = 30
                                else:
                                    minAbs = 30
                                used += 2
                                idxHr += 2
                        # "5 heures moins 20", "6 heures moins le quart"
                        elif words[idxHr] == "moins" and \
                                idxHr + 1 < len(words):
                            if words[idxHr + 1].isdigit():
                                if wordPrev in words_in:
                                    hrOffset -= 1
                                    minOffset = 60 - int(words[idxHr + 1])
                                else:
                                    hrAbs = hrAbs - 1
                                    minAbs = 60 - int(words[idxHr + 1])
                                used += 2
                                idxHr += 2
                            elif words[idxHr + 1] == "quart":
                                if wordPrev in words_in:
                                    hrOffset -= 1
                                    minOffset = 45
                                else:
                                    hrAbs = hrAbs - 1
                                    minAbs = 45
                                used += 2
                                idxHr += 2
                        # remove word minutes if present
                        if idxHr < len(words) and \
                                words[idxHr] in ["minutes", "minute"]:
                            used += 1
                            idxHr += 1
                elif wordNext == "minutes":
                    # "dans 10 minutes"
                    if wordPrev in words_in:
                        minOffset = int(word)
                    else:
                        minAbs = int(word)
                    used = 2
                elif wordNext == "secondes":
                    # "dans 5 secondes"
                    secOffset = int(word)
                    used = 2
                elif int(word) > 100:
                    # format militaire
                    hrAbs = int(word) / 100
                    minAbs = int(word) - hrAbs * 100
                    used = 1
                    if wordNext == "heures":
                        used += 1

            # handle am/pm
            if timeQualifier:
                if timeQualifier == "matin":
                    ampm = "am"
                elif timeQualifier == "après-midi":
                    ampm = "pm"
                elif timeQualifier == "soir":
                    ampm = "pm"
                elif timeQualifier == "nuit":
                    if (hrAbs or 0) > 8:
                        ampm = "pm"
                    else:
                        ampm = "am"
            hrAbs = ((hrAbs or 0) + 12 if ampm == "pm" and (hrAbs or 0) < 12
                     else hrAbs)
            hrAbs = ((hrAbs or 0) - 12 if ampm == "am" and (hrAbs or 0) >= 12
                     else hrAbs)
            if (hrAbs or 0) > 24 or ((minAbs or 0) > 59):
                isTime = False
                used = 0
            elif wordPrev in words_in:
                isTime = False
            else:
                isTime = True

        elif not hrAbs and timeQualifier:
            if timeQualifier == "matin":
                hrAbs = 8
            elif timeQualifier == "après-midi":
                hrAbs = 15
            elif timeQualifier == "soir":
                hrAbs = 19
            elif timeQualifier == "nuit":
                hrAbs = 2
            isTime = True

        if used > 0:
            # removed parsed words from the sentence
            for i in range(0, used):
                words[i + start] = ""

            if start - 1 >= 0 and words[start - 1] in markers:
                words[start - 1] = ""

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

    if hrAbs is None and minAbs is None and default_time:
        hrAbs = default_time.hour
        minAbs = default_time.minute
    if hrAbs != -1 and minAbs != -1:
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
    for idx, word in enumerate(words):
        if words[idx] == "et" and words[idx - 1] == "" and \
                words[idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())
    return [extractedDate, resultStr]


def is_fractional_fr(input_str, short_scale=True):
    """
    This function takes the given text and checks if it is a fraction.
    Args:
        input_str (str): the string to check if fractional
        short_scale (bool): use short scale if True, long scale if False
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
    if _get_ordinal_fr(input_str):
        return 1.0 / _get_ordinal_fr(input_str)
    if input_str == "trentième":
        return 1.0 / 30
    if input_str == "centième":
        return 1.0 / 100
    if input_str == "millième":
        return 1.0 / 1000

    return False


def normalize_fr(text, remove_articles=True):
    """ French string normalization """
    text = text.lower()
    words = text.split()  # this also removed extra spaces
    normalized = ""
    i = 0
    while i < len(words):
        # remove articles
        if remove_articles and words[i] in _ARTICLES_FR:
            i += 1
            continue
        if remove_articles and words[i][:2] in ["l'", "d'"]:
            words[i] = words[i][2:]
        # remove useless punctuation signs
        if words[i] in ["?", "!", ";", "…"]:
            i += 1
            continue
        # Normalize ordinal numbers
        if i > 0 and words[i - 1] in _ARTICLES_FR:
            result = _number_ordinal_fr(words, i)
            if result is not None:
                val, i = result
                normalized += " " + str(val)
                continue
        # Convert numbers into digits
        result = _number_parse_fr(words, i)
        if result is not None:
            val, i = result
            normalized += " " + str(val)
            continue

        normalized += " " + words[i]
        i += 1

    return normalized[1:]  # strip the initial space


def extract_numbers_fr(text, short_scale=True, ordinals=False):
    """
        Takes in a string and extracts a list of numbers.

    Args:
        text (str): the string to extract a number from
        short_scale (bool): Use "short scale" or "long scale" for large
            numbers -- over a million.  The default is short scale, which
            is now common in most English speaking countries.
            See https://en.wikipedia.org/wiki/Names_of_large_numbers
        ordinals (bool): consider ordinal numbers, e.g. third=3 instead of 1/3
    Returns:
        list: list of extracted numbers as floats
    """
    return extract_numbers_generic(text, pronounce_number_fr, extract_number_fr,
                                   short_scale=short_scale, ordinals=ordinals)


class FrenchNormalizer(Normalizer):
    """ TODO implement language specific normalizer"""
