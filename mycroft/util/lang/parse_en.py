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

from mycroft.util.lang.parse_common import is_numeric, look_for_fractions, \
    extract_numbers_generic
from mycroft.util.lang.format_en import NUM_STRING_EN, LONG_SCALE_EN, \
    SHORT_SCALE_EN, pronounce_number_en

SHORT_ORDINAL_STRING_EN = {
    1: 'first',
    2: 'second',
    3: 'third',
    4: 'fourth',
    5: 'fifth',
    6: 'sixth',
    7: 'seventh',
    8: 'eighth',
    9: 'ninth',
    10: 'tenth',
    11: 'eleventh',
    12: 'twelfth',
    13: 'thirteenth',
    14: 'fourteenth',
    15: 'fifteenth',
    16: 'sixteenth',
    17: 'seventeenth',
    18: 'eighteenth',
    19: 'nineteenth',
    20: 'twentieth',
    30: 'thirtieth',
    40: "fortieth",
    50: "fiftieth",
    60: "sixtieth",
    70: "seventieth",
    80: "eightieth",
    90: "ninetieth",
    10e3: "hundredth",
    1e3: "thousandth",
    1e6: "millionth",
    1e9: "billionth",
    1e12: "trillionth",
    1e15: "quadrillionth",
    1e18: "quintillionth",
    1e21: "sextillionth",
    1e24: "septillionth",
    1e27: "octillionth",
    1e30: "nonillionth",
    1e33: "decillionth"
    # TODO > 1e-33
}

LONG_ORDINAL_STRING_EN = {
    1: 'first',
    2: 'second',
    3: 'third',
    4: 'fourth',
    5: 'fifth',
    6: 'sixth',
    7: 'seventh',
    8: 'eighth',
    9: 'ninth',
    10: 'tenth',
    11: 'eleventh',
    12: 'twelfth',
    13: 'thirteenth',
    14: 'fourteenth',
    15: 'fifteenth',
    16: 'sixteenth',
    17: 'seventeenth',
    18: 'eighteenth',
    19: 'nineteenth',
    20: 'twentieth',
    30: 'thirtieth',
    40: "fortieth",
    50: "fiftieth",
    60: "sixtieth",
    70: "seventieth",
    80: "eightieth",
    90: "ninetieth",
    10e3: "hundredth",
    1e3: "thousandth",
    1e6: "millionth",
    1e12: "billionth",
    1e18: "trillionth",
    1e24: "quadrillionth",
    1e30: "quintillionth",
    1e36: "sextillionth",
    1e42: "septillionth",
    1e48: "octillionth",
    1e54: "nonillionth",
    1e60: "decillionth"
    # TODO > 1e60
}


def extractnumber_en(text, short_scale=True, ordinals=False):
    """
    This function extracts a number from a text string,
    handles pronunciations in long scale and short scale

    https://en.wikipedia.org/wiki/Names_of_large_numbers

    Args:
        text (str): the string to normalize
        short_scale (bool): use short scale if True, long scale if False
        ordinals (bool): consider ordinal numbers, third=3 instead of 1/3
    Returns:
        (int) or (float) or False: The extracted number or False if no number
                                   was found

    """

    string_num_en = {
        "half": 0.5,
        "halves": 0.5,
        "couple": 2,
        "hundred": 100,
        "hundreds": 100,
        "thousand": 1000,
        "thousands": 1000,
        "million": 1000000,
        'millions': 1000000}

    for num in NUM_STRING_EN:
        num_string = NUM_STRING_EN[num]
        string_num_en[num_string] = num

    # first, second...
    if ordinals:
        if short_scale:
            for num in SHORT_ORDINAL_STRING_EN:
                num_string = SHORT_ORDINAL_STRING_EN[num]
                string_num_en[num_string] = num
        else:
            for num in LONG_ORDINAL_STRING_EN:
                num_string = LONG_ORDINAL_STRING_EN[num]
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
            number = extractnumber_en(components[0])
            decimal = extractnumber_en(components[1])
            if number is not None and decimal is not None:
                # TODO handle number dot number number number
                if "." not in str(decimal):
                    return number + float("0." + str(decimal))

    aWords = text.split()
    aWords = [word for word in aWords if word not in ["the", "a", "an"]]
    val = False
    prev_val = None
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
        if prev_word in sums and word in string_num_en:
            if val and val < 10:
                val = prev_val + val

        # is the prev word a number and should we multiply it?
        # twenty hundred, six hundred
        if word in multiplies:
            if not prev_val:
                prev_val = 1
            val = prev_val * val

        # is this a spoken fraction?
        # half cup
        if val is False:
            val = isFractional_en(word, short_scale=short_scale)

        # 2 fifths
        if not ordinals:
            next_value = isFractional_en(next_word, short_scale=short_scale)
            if next_value:
                if not val:
                    val = 1
                val = val * next_value

        # is this a negative number?
        if val and prev_word and prev_word in negatives:
            val = 0 - val

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
    return val


def extract_datetime_en(string, dateNow, default_time):
    """ Convert a human date reference into an exact datetime

    Convert things like
        "today"
        "tomorrow afternoon"
        "next Tuesday at 4pm"
        "August 3rd"
    into a datetime.  If a reference date is not provided, the current
    local time is used.  Also consumes the words used to define the date
    returning the remaining string.  For example, the string
       "what is Tuesday's weather forecast"
    returns the date for the forthcoming Tuesday relative to the reference
    date and the remainder string
       "what is weather forecast".

    Args:
        string (str): string containing date words
        dateNow (datetime): A reference date/time for "tommorrow", etc
        default_time (time): Time to set if no time was found in the string

    Returns:
        [datetime, str]: An array containing the datetime and the remaining
                         text not consumed in the parsing, or None if no
                         date or time related text was found.
    """

    def clean_string(s):
        # clean unneeded punctuation and capitalization among other things.
        s = s.lower().replace('?', '').replace('.', '').replace(',', '') \
            .replace(' the ', ' ').replace(' a ', ' ').replace(' an ', ' ') \
            .replace("o' clock", "o'clock").replace("o clock", "o'clock") \
            .replace("o ' clock", "o'clock").replace("o 'clock", "o'clock") \
            .replace("oclock", "o'clock").replace("couple", "2") \
            .replace("centuries", "century").replace("decades", "decade") \
            .replace("millenniums", "millennium")

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
                       datestr != "" or
                       yearOffset != 0 or monthOffset != 0 or
                       dayOffset is True or hrOffset != 0 or
                       hrAbs or minOffset != 0 or
                       minAbs or secOffset != 0
               )

    if string == "" or not dateNow:
        return None

    found = False
    daySpecified = False
    dayOffset = False
    monthOffset = 0
    yearOffset = 0
    today = dateNow.strftime("%w")
    currentYear = dateNow.strftime("%Y")
    fromFlag = False
    datestr = ""
    hasYear = False
    timeQualifier = ""

    timeQualifiersAM = ['morning']
    timeQualifiersPM = ['afternoon', 'evening', 'tonight', 'night']
    timeQualifiersList = set(timeQualifiersAM + timeQualifiersPM)
    markers = ['at', 'in', 'on', 'by', 'this', 'around', 'for', 'of', "within"]
    days = ['monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'saturday', 'sunday']
    months = ['january', 'february', 'march', 'april', 'may', 'june',
              'july', 'august', 'september', 'october', 'november',
              'december']
    monthsShort = ['jan', 'feb', 'mar', 'apr', 'may', 'june', 'july', 'aug',
                   'sept', 'oct', 'nov', 'dec']
    year_multiples = ["decade", "century", "millennium"]
    day_multiples = ["weeks", "months", "years"]

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

        if word == "now" and not datestr:
            resultStr = " ".join(words[idx + 1:])
            resultStr = ' '.join(resultStr.split())
            extractedDate = dateNow.replace(microsecond=0)
            return [extractedDate, resultStr]
        elif wordNext in year_multiples:
            multiplier = None
            if is_numeric(word):
                multiplier = extractnumber_en(word)
            multiplier = multiplier or 1
            multiplier = int(multiplier)
            used += 2
            if wordNext == "decade":
                yearOffset = multiplier * 10
            elif wordNext == "century":
                yearOffset = multiplier * 100
            elif wordNext == "millennium":
                yearOffset = multiplier * 1000
        # couple of
        elif word == "2" and wordNext == "of" and \
                wordNextNext in year_multiples:
            multiplier = 2
            used += 3
            if wordNextNext == "decade":
                yearOffset = multiplier * 10
            elif wordNextNext == "century":
                yearOffset = multiplier * 100
            elif wordNextNext == "millennium":
                yearOffset = multiplier * 1000
        elif word == "2" and wordNext == "of" and \
                wordNextNext in day_multiples:
            multiplier = 2
            used += 3
            if wordNextNext == "years":
                yearOffset = multiplier
            elif wordNextNext == "months":
                monthOffset = multiplier
            elif wordNextNext == "weeks":
                dayOffset = multiplier * 7
        elif word in timeQualifiersList:
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
        # parse noon, midnight, morning, afternoon, evening
        used = 0
        if word == "noon":
            hrAbs = 12
            used += 1
        elif word == "midnight":
            hrAbs = 0
            used += 1
        elif word == "morning":
            if hrAbs is None:
                hrAbs = 8
            used += 1
        elif word == "afternoon":
            if hrAbs is None:
                hrAbs = 15
            used += 1
        elif word == "evening":
            if hrAbs is None:
                hrAbs = 19
            used += 1
        # couple of time_unit
        elif word == "2" and wordNext == "of" and \
                wordNextNext in ["hours", "minutes", "seconds"]:
            used += 3
            if wordNextNext == "hours":
                hrOffset = 2
            elif wordNextNext == "minutes":
                minOffset = 2
            elif wordNextNext == "seconds":
                secOffset = 2
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
                    if words[idx - 3] == "this":
                        daySpecified = True
                words[idx - 2] = ""
            elif wordPrev == "within":
                hrOffset = 1
            else:
                hrOffset = 1
            if wordPrevPrev in markers:
                words[idx - 2] = ""
                if wordPrevPrev == "this":
                    daySpecified = True
            words[idx - 1] = ""
            used += 1
            hrAbs = -1
            minAbs = -1
            # parse 5:00 am, 12:00 p.m., etc
        # parse in a minute
        elif word == "minute" and wordPrev == "in":
            minOffset = 1
            words[idx - 1] = ""
            used += 1
        # parse in a second
        elif word == "second" and wordPrev == "in":
            secOffset = 1
            words[idx - 1] = ""
            used += 1
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
                        daySpecified = True
                    elif wordNext == "this" and wordNextNext == "afternoon":
                        remainder = "pm"
                        used = 2
                        daySpecified = True
                    elif wordNext == "this" and wordNextNext == "evening":
                        remainder = "pm"
                        used = 2
                        daySpecified = True
                    elif wordNext == "at" and wordNextNext == "night":
                        if strHH and int(strHH) > 5:
                            remainder = "pm"
                        else:
                            remainder = "am"
                        used += 2
                    else:
                        if timeQualifier != "":
                            military = True
                            if strHH and int(strHH) <= 12 and \
                                    (timeQualifier in timeQualifiersPM):
                                strHH += str(int(strHH) + 12)
            else:
                # try to parse numbers without colons
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
                        strHH = str(int(strNum) // 100)
                        strMM = str(int(strNum) % 100)
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
                        # military time, eg. "3300 hours"
                        strHH = str(int(strNum) // 100)
                        strMM = str(int(strNum) % 100)
                        military = True
                        if wordNext == "hours" or wordNext == "hour" or \
                                remainder == "hours" or remainder == "hour":
                            used += 1
                    elif wordNext and wordNext[0].isdigit():
                        # military time, e.g. "04 38 hours"
                        strHH = strNum
                        strMM = wordNext
                        military = True
                        used += 1
                        if (wordNextNext == "hours" or
                                wordNextNext == "hour" or
                                remainder == "hours" or remainder == "hour"):
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
                        strMM = "00"
                        if wordNext == "o'clock":
                            used += 1
                        if wordNext == "in" or wordNextNext == "in":
                            used += (1 if wordNext == "in" else 2)
                            wordNextNextNext = words[idx + 3] \
                                if idx + 3 < len(words) else ""

                            if (wordNextNext and
                                    (wordNextNext in timeQualifier or
                                     wordNextNextNext in timeQualifier)):
                                if (wordNextNext in timeQualifiersPM or
                                        wordNextNextNext in timeQualifiersPM):
                                    remainder = "pm"
                                    used += 1
                                if (wordNextNext in timeQualifiersAM or
                                        wordNextNextNext in timeQualifiersAM):
                                    remainder = "am"
                                    used += 1
                        if timeQualifier != "":
                            used += 1  # TODO: Unsure if this is 100% accurate
                            military = True
                    else:
                        isTime = False

            HH = int(strHH) if strHH else 0
            MM = int(strMM) if strMM else 0
            HH = HH + 12 if remainder == "pm" and HH < 12 else HH
            HH = HH - 12 if remainder == "am" and HH >= 12 else HH

            if (not military and
                    remainder not in ['am', 'pm', 'hours', 'minutes',
                                      "second", "seconds",
                                      "hour", "minute"] and
                    ((not daySpecified) or dayOffset < 1)):
                # ambiguous time, detect whether they mean this evening or
                # the next morning based on whether it has already passed
                if dateNow.hour < HH:
                    pass  # No modification needed
                elif dateNow.hour < HH + 12:
                    HH += 12
                else:
                    # has passed, assume the next morning
                    dayOffset += 1

            if timeQualifier in timeQualifiersPM and HH < 12:
                HH += 12

            if HH > 24 or MM > 59:
                isTime = False
                used = 0
            if isTime:
                hrAbs = HH
                minAbs = MM
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
                if wordPrev == "this":
                    daySpecified = True
            if idx > 1 and wordPrevPrev in markers:
                words[idx - 2] = ""
                if wordPrevPrev == "this":
                    daySpecified = True

            idx += used - 1
            found = True

    # check that we found a date
    if not date_found:
        return None

    if dayOffset is False:
        dayOffset = 0

    # perform date manipulation

    extractedDate = dateNow.replace(microsecond=0)

    if datestr != "":
        # date included an explicit date, e.g. "june 5" or "june 2, 2017"
        try:
            temp = datetime.strptime(datestr, "%B %d")
        except ValueError:
            # Try again, allowing the year
            temp = datetime.strptime(datestr, "%B %d %Y")
        extractedDate = extractedDate.replace(hour=0, minute=0, second=0)
        if not hasYear:
            temp = temp.replace(year=extractedDate.year,
                                tzinfo=extractedDate.tzinfo)
            if extractedDate < temp:
                extractedDate = extractedDate.replace(
                    year=int(currentYear),
                    month=int(temp.strftime("%m")),
                    day=int(temp.strftime("%d")),
                    tzinfo=extractedDate.tzinfo)
            else:
                extractedDate = extractedDate.replace(
                    year=int(currentYear) + 1,
                    month=int(temp.strftime("%m")),
                    day=int(temp.strftime("%d")),
                    tzinfo=extractedDate.tzinfo)
        else:
            extractedDate = extractedDate.replace(
                year=int(temp.strftime("%Y")),
                month=int(temp.strftime("%m")),
                day=int(temp.strftime("%d")),
                tzinfo=extractedDate.tzinfo)
    else:
        # ignore the current HH:MM:SS if relative using days or greater
        if hrOffset == 0 and minOffset == 0 and secOffset == 0:
            extractedDate = extractedDate.replace(hour=0, minute=0, second=0)

    if yearOffset != 0:
        extractedDate = extractedDate + relativedelta(years=yearOffset)
    if monthOffset != 0:
        extractedDate = extractedDate + relativedelta(months=monthOffset)
    if dayOffset != 0:
        extractedDate = extractedDate + relativedelta(days=dayOffset)
    if hrAbs != -1 and minAbs != -1:
        # If no time was supplied in the string set the time to default
        # time if it's available
        if hrAbs is None and minAbs is None and default_time is not None:
            hrAbs, minAbs = default_time.hour, default_time.minute
        else:
            hrAbs = hrAbs or 0
            minAbs = minAbs or 0

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


def isFractional_en(input_str, short_scale=True):
    """
    This function takes the given text and checks if it is a fraction.

    Args:
        input_str (str): the string to check if fractional
        short_scale (bool): use short scale if True, long scale if False
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    if input_str.endswith('s', -1):
        input_str = input_str[:len(input_str) - 1]  # e.g. "fifths"

    fracts = {"whole": 1, "half": 2, "halve": 2, "quarter": 4}
    if short_scale:
        for num in SHORT_ORDINAL_STRING_EN:
            if num > 2:
                fracts[SHORT_ORDINAL_STRING_EN[num]] = num
    else:
        for num in LONG_ORDINAL_STRING_EN:
            if num > 2:
                fracts[LONG_ORDINAL_STRING_EN[num]] = num

    if input_str.lower() in fracts:
        return 1.0 / fracts[input_str.lower()]
    return False


def extract_numbers_en(text, short_scale=True, ordinals=False):
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
    return extract_numbers_generic(text, pronounce_number_en, extractnumber_en,
                                   short_scale=short_scale, ordinals=ordinals)


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

        normalized += " " + word

    # replace extracted numbers
    numbers = extract_numbers_en(normalized)
    # sort by string size, "twenty two" should be replaced before "two"
    numbers.sort(key=lambda s: len(pronounce_number_en(s)), reverse=True)
    for n in numbers:
        txt = pronounce_number_en(n)
        n = str(n)
        if n.endswith(".0"):
            n = n[:-2]
        normalized = normalized.replace(txt, n)
        # prnounced may be different from txt, ie
        # pronounce(0.5) != half
        # extract(half) == 0.5
        # TODO account for this

    return normalized[1:]  # strip the initial space
