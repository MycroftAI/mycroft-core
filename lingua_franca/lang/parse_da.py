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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lingua_franca.lang.parse_common import is_numeric, look_for_fractions, \
    extract_numbers_generic, Normalizer
from lingua_franca.lang.common_data_da import _DA_NUMBERS
from lingua_franca.lang.format_da import pronounce_number_da


def extract_number_da(text, short_scale=True, ordinals=False):
    """
    This function prepares the given text for parsing by making
    numbers consistent, getting rid of contractions, etc.
    Args:
        text (str): the string to normalize
    Returns:
        (int) or (float): The value of extracted number


    undefined articles cannot be suppressed in German:
    'ein Pferd' means 'one horse' and 'a horse'

    """
    # TODO: short_scale and ordinals don't do anything here.
    # The parameters are present in the function signature for API compatibility
    # reasons.

    text = text.lower()
    aWords = text.split()
    aWords = [word for word in aWords if
              word not in ["den", "det"]]
    and_pass = False
    valPreAnd = False
    val = False
    count = 0
    while count < len(aWords):
        word = aWords[count]
        if is_numeric(word):
            if word.isdigit():            # doesn't work with decimals
                val = float(word)
        elif is_fractional_da(word):
            val = is_fractional_da(word)
        elif is_ordinal_da(word):
            val = is_ordinal_da(word)
        else:
            if word in _DA_NUMBERS:
                val = _DA_NUMBERS[word]
                if count < (len(aWords) - 1):
                    wordNext = aWords[count + 1]
                else:
                    wordNext = ""
                valNext = is_fractional_da(wordNext)

                if valNext:
                    val = val * valNext
                    aWords[count + 1] = ""

        if not val:
            # look for fractions like "2/3"
            aPieces = word.split('/')
            # if (len(aPieces) == 2 and is_numeric(aPieces[0])
            #   and is_numeric(aPieces[1])):
            if look_for_fractions(aPieces):
                val = float(aPieces[0]) / float(aPieces[1])
            elif and_pass:
                # added to value, quit here
                val = valPreAnd
                break
            else:
                count += 1
                continue

        aWords[count] = ""

        if and_pass:
            aWords[count - 1] = ''  # remove "og"
            val += valPreAnd
        elif count + 1 < len(aWords) and aWords[count + 1] == 'og':
            and_pass = True
            valPreAnd = val
            val = False
            count += 2
            continue
        elif count + 2 < len(aWords) and aWords[count + 2] == 'og':
            and_pass = True
            valPreAnd = val
            val = False
            count += 3
            continue

        break

    return val or False


def extract_datetime_da(text, anchorDate=None, default_time=None):
    def clean_string(s):
        """
            cleans the input string of unneeded punctuation
            and capitalization among other things.

            'am' is a preposition, so cannot currently be used
            for 12 hour date format
        """

        s = s.lower().replace('?', '').replace('.', '').replace(',', '') \
            .replace(' den ', ' ').replace(' det ', ' ').replace(' om ',
                                                                 ' ').replace(
            ' om ', ' ') \
            .replace(' på ', ' ').replace(' om ', ' ')
        wordList = s.split()

        for idx, word in enumerate(wordList):
            if is_ordinal_da(word) is not False:
                word = str(is_ordinal_da(word))
                wordList[idx] = word

        return wordList

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

    timeQualifiersList = ['tidlig',
                          'morgen',
                          'morgenen',
                          'formidag',
                          'formiddagen',
                          'eftermiddag',
                          'eftermiddagen',
                          'aften',
                          'aftenen',
                          'nat',
                          'natten']
    markers = ['i', 'om', 'på', 'klokken', 'ved']
    days = ['mandag', 'tirsdag', 'onsdag',
            'torsdag', 'fredag', 'lørdag', 'søndag']
    months = ['januar', 'februar', 'marts', 'april', 'maj', 'juni',
              'juli', 'august', 'september', 'oktober', 'november',
              'desember']
    monthsShort = ['jan', 'feb', 'mar', 'apr', 'maj', 'juni', 'juli', 'aug',
                   'sep', 'okt', 'nov', 'des']

    validFollowups = days + months + monthsShort
    validFollowups.append("i dag")
    validFollowups.append("morgen")
    validFollowups.append("næste")
    validFollowups.append("forige")
    validFollowups.append("nu")

    words = clean_string(text)

    for idx, word in enumerate(words):
        if word == "":
            continue
        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""

        start = idx
        used = 0
        # save timequalifier for later
        if word in timeQualifiersList:
            timeQualifier = word
            # parse today, tomorrow, day after tomorrow
        elif word == "dag" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "morgen" and not fromFlag and wordPrev != "om" and \
                wordPrev not in days:  # morgen means tomorrow if not "am
            # Morgen" and not [day of the week] morgen
            dayOffset = 1
            used += 1
        elif word == "overmorgen" and not fromFlag:
            dayOffset = 2
            used += 1
            # parse 5 days, 10 weeks, last week, next week
        elif word == "dag" or word == "dage":
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev)
                start -= 1
                used = 2
        elif word == "uge" or word == "uger" and not fromFlag:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            elif wordPrev[:6] == "næste":
                dayOffset = 7
                start -= 1
                used = 2
            elif wordPrev[:5] == "forige":
                dayOffset = -7
                start -= 1
                used = 2
                # parse 10 months, next month, last month
        elif word == "måned" and not fromFlag:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev[:6] == "næste":
                monthOffset = 1
                start -= 1
                used = 2
            elif wordPrev[:5] == "forige":
                monthOffset = -1
                start -= 1
                used = 2
                # parse 5 years, next year, last year
        elif word == "år" and not fromFlag:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev[:6] == " næste":
                yearOffset = 1
                start -= 1
                used = 2
            elif wordPrev[:6] == "næste":
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
            if wordNext == "morgen":
                # morgen means morning if preceded by
                # the day of the week
                words[idx + 1] = "tidlig"
            if wordPrev[:6] == "næste":
                dayOffset += 7
                used += 1
                start -= 1
            elif wordPrev[:5] == "forige":
                dayOffset -= 7
                used += 1
                start -= 1
                # parse 15 of July, June 20th, Feb 18, 19 of February
        elif word in months or word in monthsShort and not fromFlag:
            try:
                m = months.index(word)
            except ValueError:
                m = monthsShort.index(word)
            used += 1
            datestr = months[m]
            if wordPrev and (wordPrev[0].isdigit() or
                             (wordPrev == "of" and wordPrevPrev[0].isdigit())):
                if wordPrev == "of" and wordPrevPrev[0].isdigit():
                    datestr += " " + words[idx - 2]
                    used += 1
                    start -= 1
                else:
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

        if (
                word == "fra" or word == "til" or word == "om") and wordNext \
                in validFollowups:
            used = 2
            fromFlag = True
            if wordNext == "morgenen" and \
                    wordPrev != "om" and \
                    wordPrev not in days:
                # morgen means tomorrow if not "am Morgen" and not
                # [day of the week] morgen:
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
                if wordNext[:6] == "næste":
                    tmpOffset += 7
                    used += 1
                    start -= 1
                elif wordNext[:5] == "forige":
                    tmpOffset -= 7
                    used += 1
                    start -= 1
                dayOffset += tmpOffset
        if used > 0:
            if start - 1 > 0 and words[start - 1].startswith("denne"):
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
    hrAbs = None
    minAbs = None

    for idx, word in enumerate(words):
        if word == "":
            continue

        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""
        wordNextNextNext = words[idx + 3] if idx + 3 < len(words) else ""
        wordNextNextNextNext = words[idx + 4] if idx + 4 < len(words) else ""

        # parse noon, midnight, morning, afternoon, evening
        used = 0
        if word[:6] == "middag":
            hrAbs = 12
            used += 1
        elif word[:11] == "midnat":
            hrAbs = 0
            used += 1
        elif word == "morgenen" or (
                wordPrev == "om" and word == "morgenen") or word == "tidlig":
            if not hrAbs:
                hrAbs = 8
            used += 1
        elif word[:11] == "eftermiddag":
            if not hrAbs:
                hrAbs = 15
            used += 1
        elif word[:5] == "aften":
            if not hrAbs:
                hrAbs = 19
            used += 1
            # parse half an hour, quarter hour
        elif word == "time" and \
                (wordPrev in markers or wordPrevPrev in markers):
            if wordPrev[:4] == "halv":
                minOffset = 30
            elif wordPrev == "kvarter":
                minOffset = 15
            elif wordPrev == "trekvarter":
                minOffset = 45
            else:
                hrOffset = 1
            if wordPrevPrev in markers:
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
                    elif nextWord == "aften":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "om" and wordNextNext == "morgenen":
                        remainder = "am"
                        used += 2
                    elif wordNext == "om" and wordNextNext == "eftermiddagen":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "om" and wordNextNext == "aftenen":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "morgen":
                        remainder = "am"
                        used += 1
                    elif wordNext == "eftermiddag":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "aften":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "i" and wordNextNext == "morgen":
                        remainder = "am"
                        used = 2
                    elif wordNext == "i" and wordNextNext == "eftermiddag":
                        remainder = "pm"
                        used = 2
                    elif wordNext == "i" and wordNextNext == "aften":
                        remainder = "pm"
                        used = 2
                    elif wordNext == "natten":
                        if strHH > 4:
                            remainder = "pm"
                        else:
                            remainder = "am"
                        used += 1
                    else:
                        if timeQualifier != "":
                            if strHH <= 12 and \
                                    (timeQualifier == "aftenen" or
                                     timeQualifier == "eftermiddagen"):
                                strHH += 12  # what happens when strHH is 24?
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
                    if wordNext == "time" and int(word) < 100:
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
                    elif wordNext == "sekund":
                        # in 5 seconds
                        secOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1

                    elif wordNext == "time":
                        strHH = word
                        used += 1
                        isTime = True
                        if wordNextNext == timeQualifier:
                            strMM = ""
                            if wordNextNext[:11] == "eftermiddag":
                                used += 1
                                remainder = "pm"
                            elif wordNextNext == "om" and wordNextNextNext == \
                                    "eftermiddagen":
                                used += 2
                                remainder = "pm"
                            elif wordNextNext[:5] == "aften":
                                used += 1
                                remainder = "pm"
                            elif wordNextNext == "om" and wordNextNextNext == \
                                    "aftenen":
                                used += 2
                                remainder = "pm"
                            elif wordNextNext[:6] == "morgen":
                                used += 1
                                remainder = "am"
                            elif wordNextNext == "om" and wordNextNextNext == \
                                    "morgenen":
                                used += 2
                                remainder = "am"
                            elif wordNextNext == "natten":
                                used += 1
                                if 8 <= int(word) <= 12:
                                    remainder = "pm"
                                else:
                                    remainder = "am"

                        elif is_numeric(wordNextNext):
                            strMM = wordNextNext
                            used += 1
                            if wordNextNextNext == timeQualifier:
                                if wordNextNextNext[:11] == "eftermiddag":
                                    used += 1
                                    remainder = "pm"
                                elif wordNextNextNext == "om" and \
                                        wordNextNextNextNext == \
                                        "eftermiddagen":
                                    used += 2
                                    remainder = "pm"
                                elif wordNextNextNext[:6] == "natten":
                                    used += 1
                                    remainder = "pm"
                                elif wordNextNextNext == "am" and \
                                        wordNextNextNextNext == "natten":
                                    used += 2
                                    remainder = "pm"
                                elif wordNextNextNext[:7] == "morgenen":
                                    used += 1
                                    remainder = "am"
                                elif wordNextNextNext == "om" and \
                                        wordNextNextNextNext == "morgenen":
                                    used += 2
                                    remainder = "am"
                                elif wordNextNextNext == "natten":
                                    used += 1
                                    if 8 <= int(word) <= 12:
                                        remainder = "pm"
                                    else:
                                        remainder = "am"

                    elif wordNext == timeQualifier:
                        strHH = word
                        strMM = 00
                        isTime = True
                        if wordNext[:10] == "eftermidag":
                            used += 1
                            remainder = "pm"
                        elif wordNext == "om" and \
                                wordNextNext == "eftermiddanen":
                            used += 2
                            remainder = "pm"
                        elif wordNext[:7] == "aftenen":
                            used += 1
                            remainder = "pm"
                        elif wordNext == "om" and wordNextNext == "aftenen":
                            used += 2
                            remainder = "pm"
                        elif wordNext[:7] == "morgenen":
                            used += 1
                            remainder = "am"
                        elif wordNext == "ao" and wordNextNext == "morgenen":
                            used += 2
                            remainder = "am"
                        elif wordNext == "natten":
                            used += 1
                            if 8 <= int(word) <= 12:
                                remainder = "pm"
                            else:
                                remainder = "am"

                # if timeQualifier != "":
                #     military = True
                # else:
                #     isTime = False

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
        if used > 0:
            # removed parsed words from the sentence
            for i in range(used):
                words[idx + i] = ""

            if wordPrev == "tidlig":
                hrOffset = -1
                words[idx - 1] = ""
                idx -= 1
            elif wordPrev == "sen":
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
        if words[idx] == "og" and words[idx - 1] == "" \
                and words[idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())

    return [extractedDate, resultStr]


def is_fractional_da(input_str, short_scale=True):
    """
    This function takes the given text and checks if it is a fraction.

    Args:
        input_str (str): the string to check if fractional
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    if input_str.lower().startswith("halv"):
        return 0.5

    if input_str.lower() == "trediedel":
        return 1.0 / 3
    elif input_str.endswith('del'):
        input_str = input_str[:len(input_str) - 3]  # e.g. "fünftel"
        if input_str.lower() in _DA_NUMBERS:
            return 1.0 / (_DA_NUMBERS[input_str.lower()])

    return False


def is_ordinal_da(input_str):
    """
    This function takes the given text and checks if it is an ordinal number.

    Args:
        input_str (str): the string to check if ordinal
    Returns:
        (bool) or (float): False if not an ordinal, otherwise the number
        corresponding to the ordinal

    ordinals for 1, 3, 7 and 8 are irregular

    only works for ordinals corresponding to the numbers in _DA_NUMBERS

    """

    lowerstr = input_str.lower()

    if lowerstr.startswith("første"):
        return 1
    if lowerstr.startswith("anden"):
        return 2
    if lowerstr.startswith("tredie"):
        return 3
    if lowerstr.startswith("fjerde"):
        return 4
    if lowerstr.startswith("femte"):
        return 5
    if lowerstr.startswith("sjette"):
        return 6
    if lowerstr.startswith("elfte"):
        return 1
    if lowerstr.startswith("tolvfte"):
        return 12

    if lowerstr[-3:] == "nde":
        # from 20 suffix is -ste*
        lowerstr = lowerstr[:-3]
        if lowerstr in _DA_NUMBERS:
            return _DA_NUMBERS[lowerstr]

    if lowerstr[-4:] in ["ende"]:
        lowerstr = lowerstr[:-4]
        if lowerstr in _DA_NUMBERS:
            return _DA_NUMBERS[lowerstr]

    if lowerstr[-2:] == "te":  # below 20 suffix is -te*
        lowerstr = lowerstr[:-2]
        if lowerstr in _DA_NUMBERS:
            return _DA_NUMBERS[lowerstr]

    return False


def normalize_da(text, remove_articles=True):
    """ German string normalization """

    words = text.split()  # this also removed extra spaces
    normalized = ""
    for word in words:
        if remove_articles and word in ["den", "det"]:
            continue

        # Convert numbers into digits, e.g. "two" -> "2"

        if word in _DA_NUMBERS:
            word = str(_DA_NUMBERS[word])

        normalized += " " + word

    return normalized[1:]  # strip the initial space


def extract_numbers_da(text, short_scale=True, ordinals=False):
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
    return extract_numbers_generic(text, pronounce_number_da, extract_number_da,
                                   short_scale=short_scale, ordinals=ordinals)


class DanishNormalizer(Normalizer):
    """ TODO implement language specific normalizer"""
