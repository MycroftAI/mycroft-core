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
from mycroft.util.lang.format_en import NUM_STRING_EN

LONG_SCALE_EN = {
    10e12: "billion",
    10e18: 'trillion',
    10e24: "quadrillion",
    10e30: "quintillion",
    10e36: "sextillion",
    10e42: "septillion",
    10e48: "octillion",
    10e54: "nonillion",
    10e60: "decillion",
    10e66: "undecillion",
    10e72: "duodecillion",
    10e78: "tredecillion",
    10e84: "quattuordecillion",
    10e90: "quinquadecillion",
    10e96: "sedecillion",
    10e102: "septendecillion",
    10e108: "octodecillion",
    10e114: "novendecillion",
    10e120: "vigintillion",
    10e306: "unquinquagintillion",
    10e312: "duoquinquagintillion",
    10e336: "sesquinquagintillion",
    10e366: "unsexagintillion",
    10e100: "googol"
}

SHORT_SCALE_EN = {
    10e9: "billion",
    10e10: 'trillion',
    10e15: "quadrillion",
    10e18: "quintillion",
    10e21: "sextillion",
    10e24: "septillion",
    10e27: "octillion",
    10e30: "nonillion",
    10e33: "decillion",
    10e36: "undecillion",
    10e39: "duodecillion",
    10e42: "tredecillion",
    10e45: "quattuordecillion",
    10e48: "quinquadecillion",
    10e51: "sedecillion",
    10e54: "septendecillion",
    10e57: "octodecillion",
    10e60: "novendecillion",
    10e63: "vigintillion",
    10e66: "unvigintillion",
    10e69: "uuovigintillion",
    10e72: "tresvigintillion",
    10e75: "quattuorvigintillion",
    10e78: "quinquavigintillion",
    10e81: "qesvigintillion",
    10e84: "septemvigintillion",
    10e87: "octovigintillion",
    10e90: "novemvigintillion",
    10e93: "trigintillion",
    10e96: "untrigintillion",
    10e99: "duotrigintillion",
    10e102: "trestrigintillion",
    10e105: "quattuortrigintillion",
    10e108: "quinquatrigintillion",
    10e111: "sestrigintillion",
    10e114: "septentrigintillion",
    10e117: "octotrigintillion",
    10e120: "noventrigintillion",
    10e123: "quadragintillion",
    10e153: "quinquagintillion",
    10e183: "sexagintillion",
    10e213: "septuagintillion",
    10e243: "octogintillion",
    10e273: "nonagintillion",
    10e303: "centillion",
    10e306: "uncentillion",
    10e309: "duocentillion",
    10e312: "trescentillion",
    10e333: "decicentillion",
    10e336: "undecicentillion",
    10e363: "viginticentillion",
    10e366: "unviginticentillion",
    10e393: "trigintacentillion",
    10e423: "quadragintacentillion",
    10e453: "quinquagintacentillion",
    10e483: "sexagintacentillion",
    10e513: "septuagintacentillion",
    10e543: "ctogintacentillion",
    10e573: "nonagintacentillion",
    10e603: "ducentillion",
    10e903: "trecentillion",
    10e1203: "quadringentillion",
    10e1503: "quingentillion",
    10e1803: "sescentillion",
    10e2103: "septingentillion",
    10e2403: "octingentillion",
    10e2703: "nongentillion",
    10e3003: "millinillion",
    10e100: "googol"
}


def extractnumber_en(text, short_scale=True):
    """
    This function extracts a number from a text string,
    handles pronunciations in long scale and short scale

    https://en.wikipedia.org/wiki/Names_of_large_numbers

    Args:
        text (str): the string to normalize
        short_scale (bool): use short scale if True, long scale if False
    Returns:
        (int) or (float) or False: The extracted number or False if no number
                                   was found

    """
    string_num_en = {"first": 1,
                     "second": 2,
                     "half": 0.5,
                     "halves": 0.5,
                     "hundreds": 100,
                     "thousands": 1000,
                     'millions': 1000000}

    for num in NUM_STRING_EN:
        num_string = NUM_STRING_EN[num]
        string_num_en[num_string] = num

    # negate next number (-2 = 0 - 2)
    negatives = ["negative", "minus"]

    # sum the next number (twenty two = 20 + 2)
    sums = ['twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty',
            'ninety']

    # multiply the previous number (one hundred = 1 * 100)
    multiplies = ["hundred", "thousand", "hundreds", "thousands", "million",
                  "millions"]

    # split sentence parse separately and sum ( 2 and a half = 2 + 0.5 )
    fraction_marker = [" and "]

    # decimal marker ( 1 point 5 = 1 + 0.5)
    decimal_marker = [" point ", " dot "]

    if short_scale:
        for num in SHORT_SCALE_EN:
            num_string = SHORT_SCALE_EN[num]
            string_num_en[num_string] = num
            string_num_en[num_string + "s"] = num
            multiplies.append(num_string)
            multiplies.append(num_string + "s")
    else:
        for num in LONG_SCALE_EN:
            num_string = LONG_SCALE_EN[num]
            string_num_en[num_string] = num
            string_num_en[num_string + "s"] = num
            multiplies.append(num_string)
            multiplies.append(num_string + "s")

    # 2 and 3/4
    for c in fraction_marker:
        components = text.split(c)

        if len(components) == 2:
            # ensure first is not a fraction and second is a fraction
            num1 = extractnumber_en(components[0])
            num2 = extractnumber_en(components[1])
            if num1 is not None and num2 is not None \
                    and num1 >= 1 and 0 < num2 < 1:
                return num1 + num2

    # 2 point 5
    for c in decimal_marker:
        components = text.split(c)
        if len(components) == 2:
            if extractnumber_en(components[0]) is not None \
                    and extractnumber_en(components[1]):
                return extractnumber_en(components[0]) + float(
                    "0." + str(extractnumber_en(components[1])).split(".")[0])

    aWords = text.split()
    aWords = [word for word in aWords if word not in ["the", "a", "an"]]
    val = False
    prev_val = None
    negative = False
    to_sum = []
    for idx, word in enumerate(aWords):

        if not word:
            continue
        prev_word = aWords[idx - 1] if idx > 0 else ""
        next_word = aWords[idx + 1] if idx + 1 < len(aWords) else ""

        # is this word already a number ?
        if is_numeric(word):
            # if word.isdigit():            # doesn't work with decimals
            val = float(word)

        # is this word the name of a number ?
        if word in string_num_en:
            val = string_num_en[word]

        # is the prev word a number and should we sum it?
        # twenty two, fifty six
        if prev_word in sums:
            val = prev_val + val

        # is the prev word a number and should we multiply it?
        # twenty hundred, six hundred
        if word in multiplies:
            if not prev_val:
                prev_val = 1
            val = prev_val * val

        # is this a spoken fraction?
        # half cup
        if not val:
            val = isFractional_en(word)

        # 2 fifths
        next_value = isFractional_en(next_word)
        if next_value:
            if not val:
                val = 1
            val = val * next_value

        # is this a negative number?
        if val and prev_word and prev_word in negatives:
            negative = True

        # let's make sure it isn't a fraction
        if not val:
            # look for fractions like "2/3"
            aPieces = word.split('/')
            if look_for_fractions(aPieces):
                val = float(aPieces[0]) / float(aPieces[1])

        else:
            prev_val = val

            # handle long numbers
            # six hundred sixty six
            # two million five hundred thousand
            if word in multiplies and next_word not in multiplies:
                to_sum.append(val)
                val = 0
                prev_val = 0

    if val is not None:
        for v in to_sum:
            val = val + v
    if negative:
        val = 0 - val
    return val


def extract_datetime_en(string, currentDate=None):
    def clean_string(s):
        """
            cleans the input string of unneeded punctuation and capitalization
            among other things.
        """
        s = s.lower().replace('?', '').replace('.', '').replace(',', '') \
            .replace(' the ', ' ').replace(' a ', ' ').replace(' an ', ' ')
        wordList = s.split()
        for idx, word in enumerate(wordList):
            word = word.replace("'s", "")

            ordinals = ["rd", "st", "nd", "th"]
            if word[0].isdigit():
                for ordinal in ordinals:
                    # "second" is the only case we should not do this
                    if ordinal in word and "second" not in word:
                        word = word.replace(ordinal, "")
            wordList[idx] = word

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

    timeQualifiersList = ['morning', 'afternoon', 'evening']
    markers = ['at', 'in', 'on', 'by', 'this', 'around', 'for', 'of']
    days = ['monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'saturday', 'sunday']
    months = ['january', 'february', 'march', 'april', 'may', 'june',
              'july', 'august', 'september', 'october', 'november',
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
        elif word == "today" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "tomorrow" and not fromFlag:
            dayOffset = 1
            used += 1
        elif (word == "day" and
              wordNext == "after" and
              wordNextNext == "tomorrow" and
              not fromFlag and
              not wordPrev[0].isdigit()):
            dayOffset = 2
            used = 3
            if wordPrev == "the":
                start -= 1
                used += 1
                # parse 5 days, 10 weeks, last week, next week
        elif word == "day":
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev)
                start -= 1
                used = 2
        elif word == "week" and not fromFlag:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            elif wordPrev == "next":
                dayOffset = 7
                start -= 1
                used = 2
            elif wordPrev == "last":
                dayOffset = -7
                start -= 1
                used = 2
                # parse 10 months, next month, last month
        elif word == "month" and not fromFlag:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "next":
                monthOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "last":
                monthOffset = -1
                start -= 1
                used = 2
                # parse 5 years, next year, last year
        elif word == "year" and not fromFlag:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "next":
                yearOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "last":
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
            if wordPrev == "next":
                dayOffset += 7
                used += 1
                start -= 1
            elif wordPrev == "last":
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
        validFollowups.append("today")
        validFollowups.append("tomorrow")
        validFollowups.append("next")
        validFollowups.append("last")
        validFollowups.append("now")
        if (word == "from" or word == "after") and wordNext in validFollowups:
            used = 2
            fromFlag = True
            if wordNext == "tomorrow":
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
                if wordNext == "next":
                    tmpOffset += 7
                    used += 1
                    start -= 1
                elif wordNext == "last":
                    tmpOffset -= 7
                    used += 1
                    start -= 1
                dayOffset += tmpOffset
        if used > 0:
            if start - 1 > 0 and words[start - 1] == "this":
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
    military = False

    for idx, word in enumerate(words):
        if word == "":
            continue

        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""
        # parse noon, midnight, morning, afternoon, evening
        used = 0
        if word == "noon":
            hrAbs = 12
            used += 1
        elif word == "midnight":
            hrAbs = 0
            used += 1
        elif word == "morning":
            if hrAbs == 0:
                hrAbs = 8
            used += 1
        elif word == "afternoon":
            if hrAbs == 0:
                hrAbs = 15
            used += 1
        elif word == "evening":
            if hrAbs == 0:
                hrAbs = 19
            used += 1
            # parse half an hour, quarter hour
        elif word == "hour" and \
                (wordPrev in markers or wordPrevPrev in markers):
            if wordPrev == "half":
                minOffset = 30
            elif wordPrev == "quarter":
                minOffset = 15
            elif wordPrevPrev == "quarter":
                minOffset = 15
                if idx > 2 and words[idx - 3] in markers:
                    words[idx - 3] = ""
                words[idx - 2] = ""
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
                            military = True
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
                    if (
                            int(strNum) > 100 and
                            (
                                    wordPrev == "o" or
                                    wordPrev == "oh"
                            )):
                        # 0800 hours (pronounced oh-eight-hundred)
                        strHH = int(strNum) / 100
                        strMM = int(strNum) - strHH * 100
                        military = True
                        if wordNext == "hours":
                            used += 1
                    elif (
                            (wordNext == "hours" or wordNext == "hour" or
                             remainder == "hours" or remainder == "hour") and
                            word[0] != '0' and
                            (
                                    int(strNum) < 100 or
                                    int(strNum) > 2400
                            )):
                        # ignores military time
                        # "in 3 hours"
                        hrOffset = int(strNum)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1

                    elif wordNext == "minutes" or wordNext == "minute" or \
                            remainder == "minutes" or remainder == "minute":
                        # "in 10 minutes"
                        minOffset = int(strNum)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif wordNext == "seconds" or wordNext == "second" \
                            or remainder == "seconds" or remainder == "second":
                        # in 5 seconds
                        secOffset = int(strNum)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif int(strNum) > 100:
                        strHH = int(strNum) / 100
                        strMM = int(strNum) - strHH * 100
                        military = True
                        if wordNext == "hours" or wordNext == "hour" or \
                                remainder == "hours" or remainder == "hour":
                            used += 1
                    elif wordNext and wordNext[0].isdigit():
                        strHH = strNum
                        strMM = wordNext
                        military = True
                        used += 1
                        if wordNext == "hours" or wordNext == "hour" or \
                                remainder == "hours" or remainder == "hour":
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
                        strHH = strNum
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
                                             wordNextNext) + 1] ==
                                         "afternoon")):
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
                        if timeQualifier != "":
                            military = True
                    else:
                        isTime = False

            # keep current date
            if not military and remainder not in ["pm", "am", "o'clock"]:
                hrOffset = hrOffset + int(dateNow.strftime("%H"))
                minOffset = minOffset + int(dateNow.strftime("%M"))
                secOffset = secOffset + int(dateNow.strftime("%S"))

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
                if idx + i >= len(words):
                    break
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
        if words[idx] == "and" and \
                words[idx - 1] == "" and words[idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())
    return [extractedDate, resultStr]


def isFractional_en(input_str):
    """
    This function takes the given text and checks if it is a fraction.

    Args:
        input_str (str): the string to check if fractional
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    if input_str.endswith('s', -1):
        input_str = input_str[:len(input_str) - 1]  # e.g. "fifths"

    aFrac = ["whole", "half", "third", "fourth", "fifth", "sixth",
             "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"]

    if input_str.lower() in aFrac:
        return 1.0 / (aFrac.index(input_str) + 1)
    if input_str == "quarter":
        return 1.0 / 4

    return False


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
                       "might've", "mustn't", "must've", "needn't",
                       "oughtn't",
                       "shan't", "she'd", "she'll", "she's", "shouldn't",
                       "should've", "somebody's", "someone'd", "someone'll",
                       "someone's", "that'll", "that's", "that'd", "there'd",
                       "there're", "there's", "they'd", "they'll", "they're",
                       "they've", "wasn't", "we'd", "we'll", "we're", "we've",
                       "weren't", "what'd", "what'll", "what're", "what's",
                       "whats",  # technically incorrect but some STT outputs
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
                         "have not", "he would", "he will", "he is",
                         "how did",
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
