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
from mycroft.util.lang.format_de import pronounce_number_de

de_numbers = {
    'null': 0,
    'ein': 1,
    'eins': 1,
    'eine': 1,
    'einer': 1,
    'einem': 1,
    'einen': 1,
    'eines': 1,
    'zwei': 2,
    'drei': 3,
    'vier': 4,
    u'fünf': 5,
    'sechs': 6,
    'sieben': 7,
    'acht': 8,
    'neun': 9,
    'zehn': 10,
    'elf': 11,
    u'zwölf': 12,
    'dreizehn': 13,
    'vierzehn': 14,
    u'fünfzehn': 15,
    'sechzehn': 16,
    'siebzehn': 17,
    'achtzehn': 18,
    'neunzehn': 19,
    'zwanzig': 20,
    'einundzwanzig': 21,
    'zweiundzwanzig': 22,
    'dreiundzwanzig': 23,
    'vierundzwanzig': 24,
    u'fünfundzwanzig': 25,
    'sechsundzwanzig': 26,
    'siebenundzwanzig': 27,
    'achtundzwanzig': 28,
    'neunundzwanzig': 29,
    u'dreißig': 30,
    u'einunddreißig': 31,
    'vierzig': 40,
    u'fünfzig': 50,
    'sechzig': 60,
    'siebzig': 70,
    'achtzig': 80,
    'neunzig': 90,
    'hundert': 100,
    'zweihundert': 200,
    'dreihundert': 300,
    'vierhundert': 400,
    u'fünfhundert': 500,
    'sechshundert': 600,
    'siebenhundert': 700,
    'achthundert': 800,
    'neunhundert': 900,
    'tausend': 1000,
    'million': 1000000
}


def extractnumber_de(text):
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
    aWords = text.split()
    aWords = [word for word in aWords if
              word not in ["der", "die", "das", "des", "den", "dem"]]
    and_pass = False
    valPreAnd = False
    val = False
    count = 0
    while count < len(aWords):
        word = aWords[count]
        if is_numeric(word):
            # if word.isdigit():            # doesn't work with decimals
            val = float(word)
        elif isFractional_de(word):
            val = isFractional_de(word)
        elif isOrdinal_de(word):
            val = isOrdinal_de(word)
        else:
            if word in de_numbers:
                val = de_numbers[word]
                if count < (len(aWords) - 1):
                    wordNext = aWords[count + 1]
                else:
                    wordNext = ""
                valNext = isFractional_de(wordNext)

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
            aWords[count - 1] = ''  # remove "and"
            val += valPreAnd
        elif count + 1 < len(aWords) and aWords[count + 1] == 'und':
            and_pass = True
            valPreAnd = val
            val = False
            count += 2
            continue
        elif count + 2 < len(aWords) and aWords[count + 2] == 'und':
            and_pass = True
            valPreAnd = val
            val = False
            count += 3
            continue

        break

    if not val:
        return False

    return val


def extract_datetime_de(string, currentDate, default_time):
    def clean_string(s):
        """
            cleans the input string of unneeded punctuation
            and capitalization among other things.

            'am' is a preposition, so cannot currently be used
            for 12 hour date format
        """

        s = s.lower().replace('?', '').replace('.', '').replace(',', '') \
            .replace(' der ', ' ').replace(' den ', ' ').replace(' an ',
                                                                 ' ').replace(
            ' am ', ' ') \
            .replace(' auf ', ' ').replace(' um ', ' ')
        wordList = s.split()

        for idx, word in enumerate(wordList):
            if isOrdinal_de(word) is not False:
                word = str(isOrdinal_de(word))
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

    timeQualifiersList = [u'früh', 'morgens', 'vormittag', 'vormittags',
                          'nachmittag', 'nachmittags', 'abend', 'abends',
                          'nachts']
    markers = ['in', 'am', 'gegen', 'bis', u'für']
    days = ['montag', 'dienstag', 'mittwoch',
            'donnerstag', 'freitag', 'samstag', 'sonntag']
    months = ['januar', 'februar', u'märz', 'april', 'mai', 'juni',
              'juli', 'august', 'september', 'october', 'november',
              'dezember']
    monthsShort = ['jan', 'feb', u'mär', 'apr', 'mai', 'juni', 'juli', 'aug',
                   'sept', 'oct', 'nov', 'dez']

    validFollowups = days + months + monthsShort
    validFollowups.append("heute")
    validFollowups.append("morgen")
    validFollowups.append(u"nächste")
    validFollowups.append(u"nächster")
    validFollowups.append(u"nächstes")
    validFollowups.append(u"nächsten")
    validFollowups.append(u"nächstem")
    validFollowups.append("letzte")
    validFollowups.append("letzter")
    validFollowups.append("letztes")
    validFollowups.append("letzten")
    validFollowups.append("letztem")
    validFollowups.append("jetzt")

    words = clean_string(string)

    for idx, word in enumerate(words):
        if word == "":
            continue
        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""

        # this isn't in clean string because I don't want to save back to words

        if word != 'morgen' and word != u'übermorgen':
            if word[-2:] == "en":
                word = word[:-2]  # remove en
        if word != 'heute':
            if word[-1:] == "e":
                word = word[:-1]  # remove plural for most nouns

        start = idx
        used = 0
        # save timequalifier for later
        if word in timeQualifiersList:
            timeQualifier = word
            # parse today, tomorrow, day after tomorrow
        elif word == "heute" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "morgen" and not fromFlag and wordPrev != "am" and \
                wordPrev not in days:  # morgen means tomorrow if not "am
            # Morgen" and not [day of the week] morgen
            dayOffset = 1
            used += 1
        elif word == u"übermorgen" and not fromFlag:
            dayOffset = 2
            used += 1
            # parse 5 days, 10 weeks, last week, next week
        elif word == "tag" or word == "tage":
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev)
                start -= 1
                used = 2
        elif word == "woch" and not fromFlag:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            elif wordPrev[:6] == u"nächst":
                dayOffset = 7
                start -= 1
                used = 2
            elif wordPrev[:5] == "letzt":
                dayOffset = -7
                start -= 1
                used = 2
                # parse 10 months, next month, last month
        elif word == "monat" and not fromFlag:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev[:6] == u"nächst":
                monthOffset = 1
                start -= 1
                used = 2
            elif wordPrev[:5] == "letzt":
                monthOffset = -1
                start -= 1
                used = 2
                # parse 5 years, next year, last year
        elif word == "jahr" and not fromFlag:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev[:6] == u"nächst":
                yearOffset = 1
                start -= 1
                used = 2
            elif wordPrev[:6] == u"nächst":
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
            if wordNext == "morgen":  # morgen means morning if preceded by
                # the day of the week
                words[idx + 1] = u"früh"
            if wordPrev[:6] == u"nächst":
                dayOffset += 7
                used += 1
                start -= 1
            elif wordPrev[:5] == "letzt":
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
                word == "von" or word == "nach" or word == "ab") and wordNext \
                in validFollowups:
            used = 2
            fromFlag = True
            if wordNext == "morgen" and wordPrev != "am" and \
                    wordPrev not in days:  # morgen means tomorrow if not "am
                #  Morgen" and not [day of the week] morgen:
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
                if wordNext[:6] == u"nächst":
                    tmpOffset += 7
                    used += 1
                    start -= 1
                elif wordNext[:5] == "letzt":
                    tmpOffset -= 7
                    used += 1
                    start -= 1
                dayOffset += tmpOffset
        if used > 0:
            if start - 1 > 0 and words[start - 1].startswith("diese"):
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
        if word[:6] == "mittag":
            hrAbs = 12
            used += 1
        elif word[:11] == "mitternacht":
            hrAbs = 0
            used += 1
        elif word == "morgens" or (
                wordPrev == "am" and word == "morgen") or word == u"früh":
            if not hrAbs:
                hrAbs = 8
            used += 1
        elif word[:10] == "nachmittag":
            if not hrAbs:
                hrAbs = 15
            used += 1
        elif word[:5] == "abend":
            if not hrAbs:
                hrAbs = 19
            used += 1
            # parse half an hour, quarter hour
        elif word == "stunde" and \
                (wordPrev in markers or wordPrevPrev in markers):
            if wordPrev[:4] == "halb":
                minOffset = 30
            elif wordPrev == "viertel":
                minOffset = 15
            elif wordPrev == "dreiviertel":
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
                    elif nextWord == "abends":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "am" and wordNextNext == "morgen":
                        remainder = "am"
                        used += 2
                    elif wordNext == "am" and wordNextNext == "nachmittag":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "am" and wordNextNext == "abend":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "morgens":
                        remainder = "am"
                        used += 1
                    elif wordNext == "nachmittags":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "abends":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "heute" and wordNextNext == "morgen":
                        remainder = "am"
                        used = 2
                    elif wordNext == "heute" and wordNextNext == "nachmittag":
                        remainder = "pm"
                        used = 2
                    elif wordNext == "heute" and wordNextNext == "abend":
                        remainder = "pm"
                        used = 2
                    elif wordNext == "nachts":
                        if strHH > 4:
                            remainder = "pm"
                        else:
                            remainder = "am"
                        used += 1
                    else:
                        if timeQualifier != "":
                            if strHH <= 12 and \
                                    (timeQualifier == "abends" or
                                     timeQualifier == "nachmittags"):
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
                    if wordNext == "stund" and int(word) < 100:
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

                    elif wordNext == "uhr":
                        strHH = word
                        used += 1
                        isTime = True
                        if wordNextNext == timeQualifier:
                            strMM = ""
                            if wordNextNext[:10] == "nachmittag":
                                used += 1
                                remainder = "pm"
                            elif wordNextNext == "am" and wordNextNextNext == \
                                    "nachmittag":
                                used += 2
                                remainder = "pm"
                            elif wordNextNext[:5] == "abend":
                                used += 1
                                remainder = "pm"
                            elif wordNextNext == "am" and wordNextNextNext == \
                                    "abend":
                                used += 2
                                remainder = "pm"
                            elif wordNextNext[:7] == "morgens":
                                used += 1
                                remainder = "am"
                            elif wordNextNext == "am" and wordNextNextNext == \
                                    "morgen":
                                used += 2
                                remainder = "am"
                            elif wordNextNext == "nachts":
                                used += 1
                                if 8 <= int(word) <= 12:
                                    remainder = "pm"
                                else:
                                    remainder = "am"

                        elif is_numeric(wordNextNext):
                            strMM = wordNextNext
                            used += 1
                            if wordNextNextNext == timeQualifier:
                                if wordNextNextNext[:10] == "nachmittag":
                                    used += 1
                                    remainder = "pm"
                                elif wordNextNextNext == "am" and \
                                        wordNextNextNextNext == "nachmittag":
                                    used += 2
                                    remainder = "pm"
                                elif wordNextNextNext[:5] == "abend":
                                    used += 1
                                    remainder = "pm"
                                elif wordNextNextNext == "am" and \
                                        wordNextNextNextNext == "abend":
                                    used += 2
                                    remainder = "pm"
                                elif wordNextNextNext[:7] == "morgens":
                                    used += 1
                                    remainder = "am"
                                elif wordNextNextNext == "am" and \
                                        wordNextNextNextNext == "morgen":
                                    used += 2
                                    remainder = "am"
                                elif wordNextNextNext == "nachts":
                                    used += 1
                                    if 8 <= int(word) <= 12:
                                        remainder = "pm"
                                    else:
                                        remainder = "am"

                    elif wordNext == timeQualifier:
                        strHH = word
                        strMM = 00
                        isTime = True
                        if wordNext[:10] == "nachmittag":
                            used += 1
                            remainder = "pm"
                        elif wordNext == "am" and wordNextNext == "nachmittag":
                            used += 2
                            remainder = "pm"
                        elif wordNext[:5] == "abend":
                            used += 1
                            remainder = "pm"
                        elif wordNext == "am" and wordNextNext == "abend":
                            used += 2
                            remainder = "pm"
                        elif wordNext[:7] == "morgens":
                            used += 1
                            remainder = "am"
                        elif wordNext == "am" and wordNextNext == "morgen":
                            used += 2
                            remainder = "am"
                        elif wordNext == "nachts":
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

            if wordPrev == "Uhr":
                words[words.index(wordPrev)] = ""

            if wordPrev == u"früh":
                hrOffset = -1
                words[idx - 1] = ""
                idx -= 1
            elif wordPrev == u"spät":
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
        if words[idx] == "und" and words[idx - 1] == "" \
                and words[idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())

    return [extractedDate, resultStr]


def isFractional_de(input_str):
    """
    This function takes the given text and checks if it is a fraction.

    Args:
        input_str (str): the string to check if fractional
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    if input_str.lower().startswith("halb"):
        return 0.5

    if input_str.lower() == "drittel":
        return 1.0 / 3
    elif input_str.endswith('tel'):
        if input_str.endswith('stel'):
            input_str = input_str[:len(input_str) - 4]  # e.g. "hundertstel"
        else:
            input_str = input_str[:len(input_str) - 3]  # e.g. "fünftel"
        if input_str.lower() in de_numbers:
            return 1.0 / (de_numbers[input_str.lower()])

    return False


def isOrdinal_de(input_str):
    """
    This function takes the given text and checks if it is an ordinal number.

    Args:
        input_str (str): the string to check if ordinal
    Returns:
        (bool) or (float): False if not an ordinal, otherwise the number
        corresponding to the ordinal

    ordinals for 1, 3, 7 and 8 are irregular

    only works for ordinals corresponding to the numbers in de_numbers

    """

    lowerstr = input_str.lower()

    if lowerstr.startswith("erste"):
        return 1
    if lowerstr.startswith("dritte"):
        return 3
    if lowerstr.startswith("siebte"):
        return 7
    if lowerstr.startswith("achte"):
        return 8

    if lowerstr[-3:] == "ste":  # from 20 suffix is -ste*
        lowerstr = lowerstr[:-3]
        if lowerstr in de_numbers:
            return de_numbers[lowerstr]

    if lowerstr[-4:] in ["ster", "stes", "sten", "stem"]:
        lowerstr = lowerstr[:-4]
        if lowerstr in de_numbers:
            return de_numbers[lowerstr]

    if lowerstr[-2:] == "te":  # below 20 suffix is -te*
        lowerstr = lowerstr[:-2]
        if lowerstr in de_numbers:
            return de_numbers[lowerstr]

    if lowerstr[-3:] in ["ter", "tes", "ten", "tem"]:
        lowerstr = lowerstr[:-3]
        if lowerstr in de_numbers:
            return de_numbers[lowerstr]

    return False


def normalize_de(text, remove_articles):
    """ German string normalization """

    words = text.split()  # this also removed extra spaces
    normalized = ""
    for word in words:
        if remove_articles and word in ["der", "die", "das", "des", "den",
                                        "dem"]:
            continue

        # Expand common contractions, e.g. "isn't" -> "is not"
        contraction = ["net", "nett"]
        if word in contraction:
            expansion = ["nicht", "nicht"]
            word = expansion[contraction.index(word)]

        # Convert numbers into digits, e.g. "two" -> "2"

        if word in de_numbers:
            word = str(de_numbers[word])

        normalized += " " + word

    return normalized[1:]  # strip the initial space


def extract_numbers_de(text, short_scale=True, ordinals=False):
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
    return extract_numbers_generic(text, pronounce_number_de, extractnumber_de,
                                   short_scale=short_scale, ordinals=ordinals)
