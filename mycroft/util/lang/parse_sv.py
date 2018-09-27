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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from mycroft.util.lang.parse_common import is_numeric, look_for_fractions


def extractnumber_sv(text):
    """
    This function prepares the given text for parsing by making
    numbers consistent, getting rid of contractions, etc.
    Args:
        text (str): the string to normalize
    Returns:
        (int) or (float): The value of extracted number
    """
    aWords = text.split()
    and_pass = False
    valPreAnd = False
    val = False
    count = 0
    while count < len(aWords):
        word = aWords[count]
        if is_numeric(word):
            val = float(word)
        elif word == "första":
            val = 1
        elif word == "andra":
            val = 2
        elif word == "tredje":
            val = 3
        elif word == "fjärde":
            val = 4
        elif word == "femte":
            val = 5
        elif word == "sjätte":
            val = 6
        elif is_fractional_sv(word):
            val = is_fractional_sv(word)
        else:
            if word == "en":
                val = 1
            if word == "ett":
                val = 1
            elif word == "två":
                val = 2
            elif word == "tre":
                val = 3
            elif word == "fyra":
                val = 4
            elif word == "fem":
                val = 5
            elif word == "sex":
                val = 6
            elif word == "sju":
                val = 7
            elif word == "åtta":
                val = 8
            elif word == "nio":
                val = 9
            elif word == "tio":
                val = 10
            if val:
                if count < (len(aWords) - 1):
                    wordNext = aWords[count + 1]
                else:
                    wordNext = ""
                valNext = is_fractional_sv(wordNext)

                if valNext:
                    val = val * valNext
                    aWords[count + 1] = ""

        if not val:
            # look for fractions like "2/3"
            aPieces = word.split('/')
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
            aWords[count - 1] = ''  # remove "och"
            val += valPreAnd
        elif count + 1 < len(aWords) and aWords[count + 1] == 'och':
            and_pass = True
            valPreAnd = val
            val = False
            count += 2
            continue
        elif count + 2 < len(aWords) and aWords[count + 2] == 'och':
            and_pass = True
            valPreAnd = val
            val = False
            count += 3
            continue

        break

    if not val:
        return False

    return val


def extract_datetime_sv(string, currentDate, default_time):
    def clean_string(s):
        """
            cleans the input string of unneeded punctuation and capitalization
            among other things.
        """
        s = s.lower().replace('?', '').replace('.', '').replace(',', '') \
            .replace(' den ', ' ').replace(' en ', ' ')
        wordList = s.split()
        for idx, word in enumerate(wordList):
            word = word.replace("'s", "")

            ordinals = ["rd", "st", "nd", "th"]
            if word[0].isdigit():
                for ordinal in ordinals:
                    if ordinal in word:
                        word = word.replace(ordinal, "")
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

    if string == "" or not currentDate:
        return None

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

    timeQualifiersList = ['morgon', 'förmiddag', 'eftermiddag', 'kväll']
    markers = ['på', 'i', 'den här', 'kring', 'efter']
    days = ['måndag', 'tisdag', 'onsdag', 'torsdag',
            'fredag', 'lördag', 'söndag']
    months = ['januari', 'februari', 'mars', 'april', 'maj', 'juni',
              'juli', 'augusti', 'september', 'oktober', 'november',
              'december']
    monthsShort = ['jan', 'feb', 'mar', 'apr', 'may', 'june', 'july', 'aug',
                   'sept', 'oct', 'nov', 'dec']

    words = clean_string(string)

    for idx, word in enumerate(words):
        if word == "":
            continue
        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""

        # this isn't in clean string because I don't want to save back to words
        word = word.rstrip('s')
        start = idx
        used = 0
        # save timequalifier for later
        if word in timeQualifiersList:
            timeQualifier = word
            # parse today, tomorrow, day after tomorrow
        elif word == "idag" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "imorgon" and not fromFlag:
            dayOffset = 1
            used += 1
        elif word == "morgondagen" or word == "morgondagens" and not fromFlag:
            dayOffset = 1
            used += 1
        elif word == "övermorgon" and not fromFlag:
            dayOffset = 2
            used += 1
        # parse 5 days, 10 weeks, last week, next week
        elif word == "dag" or word == "dagar":
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev)
                start -= 1
                used = 2
        elif word == "vecka" or word == "veckor" and not fromFlag:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            elif wordPrev == "nästa":
                dayOffset = 7
                start -= 1
                used = 2
            elif wordPrev == "förra":
                dayOffset = -7
                start -= 1
                used = 2
                # parse 10 months, next month, last month
        elif word == "månad" and not fromFlag:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "nästa":
                monthOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "förra":
                monthOffset = -1
                start -= 1
                used = 2
                # parse 5 years, next year, last year
        elif word == "år" and not fromFlag:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "nästa":
                yearOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "förra":
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
            if wordPrev == "nästa":
                dayOffset += 7
                used += 1
                start -= 1
            elif wordPrev == "förra":
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
        validFollowups = days + months + monthsShort
        validFollowups.append("idag")
        validFollowups.append("imorgon")
        validFollowups.append("nästa")
        validFollowups.append("förra")
        validFollowups.append("nu")
        if (word == "från" or word == "efter") and wordNext in validFollowups:
            used = 2
            fromFlag = True
            if wordNext == "imorgon":
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
                if wordNext == "nästa":
                    tmpOffset += 7
                    used += 1
                    start -= 1
                elif wordNext == "förra":
                    tmpOffset -= 7
                    used += 1
                    start -= 1
                dayOffset += tmpOffset
        if used > 0:
            if start - 1 > 0 and words[start - 1] == "denna":
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
        # parse noon, midnight, morning, afternoon, evening
        used = 0
        if word == "middag":
            hrAbs = 12
            used += 1
        elif word == "midnatt":
            hrAbs = 0
            used += 1
        elif word == "morgon":
            if not hrAbs:
                hrAbs = 8
            used += 1
        elif word == "förmiddag":
            if not hrAbs:
                hrAbs = 10
            used += 1
        elif word == "eftermiddag":
            if not hrAbs:
                hrAbs = 15
            used += 1
        elif word == "kväll":
            if not hrAbs:
                hrAbs = 19
            used += 1
            # parse half an hour, quarter hour
        elif wordPrev in markers or wordPrevPrev in markers:
            if word == "halvtimme" or word == "halvtimma":
                minOffset = 30
            elif word == "kvart":
                minOffset = 15
            elif word == "timme" or word == "timma":
                hrOffset = 1
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
                    elif nextWord == "tonight":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "in" and wordNextNext == "the" and \
                            words[idx + 3] == "morning":
                        remainder = "am"
                        used += 3
                    elif wordNext == "in" and wordNextNext == "the" and \
                            words[idx + 3] == "afternoon":
                        remainder = "pm"
                        used += 3
                    elif wordNext == "in" and wordNextNext == "the" and \
                            words[idx + 3] == "evening":
                        remainder = "pm"
                        used += 3
                    elif wordNext == "in" and wordNextNext == "morning":
                        remainder = "am"
                        used += 2
                    elif wordNext == "in" and wordNextNext == "afternoon":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "in" and wordNextNext == "evening":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "this" and wordNextNext == "morning":
                        remainder = "am"
                        used = 2
                    elif wordNext == "this" and wordNextNext == "afternoon":
                        remainder = "pm"
                        used = 2
                    elif wordNext == "this" and wordNextNext == "evening":
                        remainder = "pm"
                        used = 2
                    elif wordNext == "at" and wordNextNext == "night":
                        if strHH > 5:
                            remainder = "pm"
                        else:
                            remainder = "am"
                        used += 2
                    else:
                        if timeQualifier != "":
                            if strHH <= 12 and \
                                    (timeQualifier == "evening" or
                                     timeQualifier == "afternoon"):
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
                        if wordNext == "hours":
                            used += 1
                    elif (
                            wordNext == "hours" and
                            word[0] != '0' and
                            (
                                int(word) < 100 and
                                int(word) > 2400
                            )):
                        # "in 3 hours"
                        hrOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1

                    elif wordNext == "minutes":
                        # "in 10 minutes"
                        minOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif wordNext == "seconds":
                        # in 5 seconds
                        secOffset = int(word)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif int(word) > 100:
                        strHH = int(word) / 100
                        strMM = int(word) - strHH * 100
                        if wordNext == "hours":
                            used += 1
                    elif wordNext[0].isdigit():
                        strHH = word
                        strMM = wordNext
                        used += 1
                        if wordNextNext == "hours":
                            used += 1
                    elif (
                            wordNext == "" or wordNext == "o'clock" or
                            (
                                        wordNext == "in" and
                                        (
                                            wordNextNext == "the" or
                                            wordNextNext == timeQualifier
                                        )
                            )):
                        strHH = word
                        strMM = 00
                        if wordNext == "o'clock":
                            used += 1
                        if wordNext == "in" or wordNextNext == "in":
                            used += (1 if wordNext == "in" else 2)
                            if (wordNextNext and
                                wordNextNext in timeQualifier or
                                (words[words.index(wordNextNext) + 1] and
                                 words[words.index(wordNextNext) + 1] in
                                 timeQualifier)):
                                if (wordNextNext == "afternoon" or
                                    (len(words) >
                                     words.index(wordNextNext) + 1 and
                                     words[words.index(
                                         wordNextNext) + 1] == "afternoon")):
                                    remainder = "pm"
                                if (wordNextNext == "evening" or
                                    (len(words) >
                                     (words.index(wordNextNext) + 1) and
                                     words[words.index(
                                         wordNextNext) + 1] == "evening")):
                                    remainder = "pm"
                                if (wordNextNext == "morning" or
                                    (len(words) >
                                     words.index(wordNextNext) + 1 and
                                     words[words.index(
                                         wordNextNext) + 1] == "morning")):
                                    remainder = "am"
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
        if used > 0:
            # removed parsed words from the sentence
            for i in range(used):
                words[idx + i] = ""

            if wordPrev == "o" or wordPrev == "oh":
                words[words.index(wordPrev)] = ""

            if wordPrev == "early":
                hrOffset = -1
                words[idx - 1] = ""
                idx -= 1
            elif wordPrev == "late":
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
        if words[idx] == "and" and words[idx - 1] == "" and words[
                idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())
    return [extractedDate, resultStr]


def is_fractional_sv(input_str):
    """
    This function takes the given text and checks if it is a fraction.

    Args:
        input_str (str): the string to check if fractional
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    if input_str.endswith('ars', -3):
        input_str = input_str[:len(input_str) - 3]  # e.g. "femtedelar"
    if input_str.endswith('ar', -2):
        input_str = input_str[:len(input_str) - 2]  # e.g. "femtedelar"
    if input_str.endswith('a', -1):
        input_str = input_str[:len(input_str) - 1]  # e.g. "halva"
    if input_str.endswith('s', -1):
        input_str = input_str[:len(input_str) - 1]  # e.g. "halva"

    aFrac = ["hel", "halv", "tredjedel", "fjärdedel", "femtedel", "sjättedel",
             "sjundedel", "åttondel", "niondel", "tiondel", "elftedel",
             "tolftedel"]
    if input_str.lower() in aFrac:
        return 1.0 / (aFrac.index(input_str) + 1)
    if input_str == "kvart":
        return 1.0 / 4
    if input_str == "trekvart":
        return 3.0 / 4

    return False


def normalize_sv(text, remove_articles):
    """ English string normalization """

    words = text.split()  # this also removed extra spaces
    normalized = ''
    for word in words:
        # Convert numbers into digits, e.g. "two" -> "2"
        if word == 'en':
            word = 'ett'
        textNumbers = ["noll", "ett", "två", "tre", "fyra", "fem", "sex",
                       "sju", "åtta", "nio", "tio", "elva", "tolv",
                       "tretton", "fjorton", "femton", "sexton",
                       "sjutton", "arton", "nitton", "tjugo"]
        if word in textNumbers:
            word = str(textNumbers.index(word))

        normalized += " " + word

    return normalized[1:]  # strip the initial space
