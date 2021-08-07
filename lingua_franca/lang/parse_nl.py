#
# Copyright 2019 Mycroft AI Inc.
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
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from .parse_common import is_numeric, look_for_fractions, Token, \
    ReplaceableNumber, tokenize, partition_list, Normalizer, invert_dict
from .common_data_nl import _SHORT_ORDINAL_STRING_NL, _ARTICLES_NL, \
    _DECIMAL_MARKER_NL, _FRACTION_MARKER_NL, _LONG_ORDINAL_STRING_NL,\
    _LONG_SCALE_NL, _MULTIPLIES_LONG_SCALE_NL, _MULTIPLIES_SHORT_SCALE_NL,\
    _NEGATIVES_NL, _SHORT_SCALE_NL, _STRING_LONG_ORDINAL_NL, _STRING_NUM_NL, \
    _STRING_SHORT_ORDINAL_NL, _SUMS_NL
import re


def _convert_words_to_numbers_nl(text, short_scale=True, ordinals=False):
    """Convert words in a string into their equivalent numbers.
    Args:
        text str:
        short_scale boolean: True if short scale numbers should be used.
        ordinals boolean: True if ordinals (e.g. first, second, third) should
                          be parsed to their number values (1, 2, 3...)

    Returns:
        str
        The original text, with numbers subbed in where appropriate.
    """
    text = text.lower()
    tokens = tokenize(text)
    numbers_to_replace = \
        _extract_numbers_with_text_nl(tokens, short_scale, ordinals)
    numbers_to_replace.sort(key=lambda number: number.start_index)

    results = []
    for token in tokens:
        if not numbers_to_replace or \
                token.index < numbers_to_replace[0].start_index:
            results.append(token.word)
        else:
            if numbers_to_replace and \
                    token.index == numbers_to_replace[0].start_index:
                results.append(str(numbers_to_replace[0].value))
            if numbers_to_replace and \
                    token.index == numbers_to_replace[0].end_index:
                numbers_to_replace.pop(0)

    return ' '.join(results)


def _extract_numbers_with_text_nl(tokens, short_scale=True,
                                  ordinals=False, fractional_numbers=True):
    """Extract all numbers from a list of _Tokens, with the representing words.

    Args:
        [Token]: The tokens to parse.
        short_scale bool: True if short scale numbers should be used, False for
                          long scale. True by default.
        ordinals bool: True if ordinal words (first, second, third, etc) should
                       be parsed.
        fractional_numbers bool: True if we should look for fractions and
                                 decimals.

    Returns:
        [_ReplaceableNumber]: A list of tuples, each containing a number and a
                         string.
    """
    placeholder = "<placeholder>"  # inserted to maintain correct indices
    results = []
    while True:
        to_replace = \
            _extract_number_with_text_nl(tokens, short_scale,
                                         ordinals, fractional_numbers)

        if not to_replace:
            break

        results.append(to_replace)

        tokens = [
            t if not
            to_replace.start_index <= t.index <= to_replace.end_index
            else
            Token(placeholder, t.index) for t in tokens
        ]
    results.sort(key=lambda n: n.start_index)
    return results


def _extract_number_with_text_nl(tokens, short_scale=True,
                                 ordinals=False, fractional_numbers=True):
    """This function extracts a number from a list of _Tokens.

    Args:
        tokens str: the string to normalize
        short_scale (bool): use short scale if True, long scale if False
        ordinals (bool): consider ordinal numbers, third=3 instead of 1/3
        fractional_numbers (bool): True if we should look for fractions and
                                   decimals.
    Returns:
        _ReplaceableNumber
    """
    number, tokens = \
        _extract_number_with_text_nl_helper(tokens, short_scale,
                                            ordinals, fractional_numbers)
    while tokens and tokens[0].word in _ARTICLES_NL:
        tokens.pop(0)
    return ReplaceableNumber(number, tokens)


def _extract_number_with_text_nl_helper(tokens,
                                        short_scale=True, ordinals=False,
                                        fractional_numbers=True):
    """Helper for _extract_number_with_text_nl.

    This contains the real logic for parsing, but produces
    a result that needs a little cleaning (specific, it may
    contain leading articles that can be trimmed off).

    Args:
        tokens [Token]:
        short_scale boolean:
        ordinals boolean:
        fractional_numbers boolean:

    Returns:
        int or float, [_Tokens]
    """
    if fractional_numbers:
        fraction, fraction_text = \
            _extract_fraction_with_text_nl(tokens, short_scale, ordinals)
        if fraction:
            return fraction, fraction_text

        decimal, decimal_text = \
            _extract_decimal_with_text_nl(tokens, short_scale, ordinals)
        if decimal:
            return decimal, decimal_text

    return _extract_whole_number_with_text_nl(tokens, short_scale, ordinals)


def _extract_fraction_with_text_nl(tokens, short_scale, ordinals):
    """Extract fraction numbers from a string.

    This function handles text such as '2 and 3/4'. Note that "one half" or
    similar will be parsed by the whole number function.

    Args:
        tokens [Token]: words and their indexes in the original string.
        short_scale boolean:
        ordinals boolean:

    Returns:
        (int or float, [Token])
        The value found, and the list of relevant tokens.
        (None, None) if no fraction value is found.
    """
    for c in _FRACTION_MARKER_NL:
        partitions = partition_list(tokens, lambda t: t.word == c)

        if len(partitions) == 3:
            numbers1 = \
                _extract_numbers_with_text_nl(partitions[0], short_scale,
                                              ordinals, fractional_numbers=False)
            numbers2 = \
                _extract_numbers_with_text_nl(partitions[2], short_scale,
                                              ordinals, fractional_numbers=True)

            if not numbers1 or not numbers2:
                return None, None

            # ensure first is not a fraction and second is a fraction
            num1 = numbers1[-1]
            num2 = numbers2[0]
            if num1.value >= 1 and 0 < num2.value < 1:
                return num1.value + num2.value, \
                    num1.tokens + partitions[1] + num2.tokens

    return None, None


def _extract_decimal_with_text_nl(tokens, short_scale, ordinals):
    """Extract decimal numbers from a string.

    This function handles text such as '2 point 5'.

    Notes:
        While this is a helper for extractnumber_nl, it also depends on
        extractnumber_nl, to parse out the components of the decimal.

        This does not currently handle things like:
            number dot number number number

    Args:
        tokens [Token]: The text to parse.
        short_scale boolean:
        ordinals boolean:

    Returns:
        (float, [Token])
        The value found and relevant tokens.
        (None, None) if no decimal value is found.
    """
    for c in _DECIMAL_MARKER_NL:
        partitions = partition_list(tokens, lambda t: t.word == c)

        if len(partitions) == 3:
            numbers1 = \
                _extract_numbers_with_text_nl(partitions[0], short_scale,
                                              ordinals, fractional_numbers=False)
            numbers2 = \
                _extract_numbers_with_text_nl(partitions[2], short_scale,
                                              ordinals, fractional_numbers=False)

            if not numbers1 or not numbers2:
                return None, None

            number = numbers1[-1]
            decimal = numbers2[0]

            # TODO handle number dot number number number
            if "." not in str(decimal.text):
                return number.value + float('0.' + str(decimal.value)), \
                    number.tokens + partitions[1] + decimal.tokens
    return None, None


def _extract_whole_number_with_text_nl(tokens, short_scale, ordinals):
    """Handle numbers not handled by the decimal or fraction functions.

    This is generally whole numbers. Note that phrases such as "one half" will
    be handled by this function, while "one and a half" are handled by the
    fraction function.

    Args:
        tokens [Token]:
        short_scale boolean:
        ordinals boolean:

    Returns:
        int or float, [_Tokens]
        The value parsed, and tokens that it corresponds to.
    """
    multiplies, string_num_ordinal, string_num_scale = \
        _initialize_number_data_nl(short_scale)

    number_words = []  # type: [Token]
    val = False
    prev_val = None
    next_val = None
    to_sum = []
    for idx, token in enumerate(tokens):
        current_val = None
        if next_val:
            next_val = None
            continue

        word = token.word
        if word in _ARTICLES_NL or word in _NEGATIVES_NL:
            number_words.append(token)
            continue

        prev_word = tokens[idx - 1].word if idx > 0 else ""
        next_word = tokens[idx + 1].word if idx + 1 < len(tokens) else ""

        if word not in string_num_scale and \
                word not in _STRING_NUM_NL and \
                word not in _SUMS_NL and \
                word not in multiplies and \
                not (ordinals and word in string_num_ordinal) and \
                not is_numeric(word) and \
                not is_fractional_nl(word, short_scale=short_scale) and \
                not look_for_fractions(word.split('/')):
            words_only = [token.word for token in number_words]
            if number_words and not all([w in _ARTICLES_NL |
                                         _NEGATIVES_NL for w in words_only]):
                break
            else:
                number_words = []
                continue
        elif word not in multiplies \
                and prev_word not in multiplies \
                and prev_word not in _SUMS_NL \
                and not (ordinals and prev_word in string_num_ordinal) \
                and prev_word not in _NEGATIVES_NL \
                and prev_word not in _ARTICLES_NL:
            number_words = [token]
        elif prev_word in _SUMS_NL and word in _SUMS_NL:
            number_words = [token]
        else:
            number_words.append(token)

        # is this word already a number ?
        if is_numeric(word):
            if word.isdigit():            # doesn't work with decimals
                val = int(word)
            else:
                val = float(word)
            current_val = val

        # is this word the name of a number ?
        if word in _STRING_NUM_NL:
            val = _STRING_NUM_NL.get(word)
            current_val = val
        elif word in string_num_scale:
            val = string_num_scale.get(word)
            current_val = val
        elif ordinals and word in string_num_ordinal:
            val = string_num_ordinal[word]
            current_val = val

        # is the prev word an ordinal number and current word is one?
        # second one, third one
        if ordinals and prev_word in string_num_ordinal and val == 1:
            val = prev_val

        # is the prev word a number and should we sum it?
        # twenty two, fifty six
        if prev_word in _SUMS_NL and val and val < 10:
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
            val = is_fractional_nl(word, short_scale=short_scale)
            current_val = val

        # 2 fifths
        if not ordinals:
            next_val = is_fractional_nl(next_word, short_scale=short_scale)
            if next_val:
                if not val:
                    val = 1
                val = val * next_val
                number_words.append(tokens[idx + 1])

        # is this a negative number?
        if val and prev_word and prev_word in _NEGATIVES_NL:
            val = 0 - val

        # let's make sure it isn't a fraction
        if not val:
            # look for fractions like "2/3"
            aPieces = word.split('/')
            if look_for_fractions(aPieces):
                val = float(aPieces[0]) / float(aPieces[1])
                current_val = val

        else:
            if prev_word in _SUMS_NL and word not in _SUMS_NL and current_val >= 10:
                # Backtrack - we've got numbers we can't sum.
                number_words.pop()
                val = prev_val
                break
            prev_val = val

            # handle long numbers
            # six hundred sixty six
            # two million five hundred thousand
            if word in multiplies and next_word not in multiplies:
                to_sum.append(val)
                val = 0
                prev_val = 0

    if val is not None and to_sum:
        val += sum(to_sum)

    return val, number_words


def _initialize_number_data_nl(short_scale):
    """Generate dictionaries of words to numbers, based on scale.

    This is a helper function for _extract_whole_number.

    Args:
        short_scale boolean:

    Returns:
        (set(str), dict(str, number), dict(str, number))
        multiplies, string_num_ordinal, string_num_scale
    """
    multiplies = _MULTIPLIES_SHORT_SCALE_NL if short_scale \
        else _MULTIPLIES_LONG_SCALE_NL

    string_num_ordinal_nl = _STRING_SHORT_ORDINAL_NL if short_scale \
        else _STRING_LONG_ORDINAL_NL

    string_num_scale_nl = _SHORT_SCALE_NL if short_scale else _LONG_SCALE_NL
    string_num_scale_nl = invert_dict(string_num_scale_nl)

    return multiplies, string_num_ordinal_nl, string_num_scale_nl


def extract_number_nl(text, short_scale=True, ordinals=False):
    """Extract a number from a text string

    The function handles pronunciations in long scale and short scale

    https://en.wikipedia.org/wiki/Names_of_large_numbers

    Args:
        text (str): the string to normalize
        short_scale (bool): use short scale if True, long scale if False
        ordinals (bool): consider ordinal numbers, third=3 instead of 1/3
    Returns:
        (int) or (float) or False: The extracted number or False if no number
                                   was found
    """
    return _extract_number_with_text_nl(tokenize(text.lower()),
                                        short_scale, ordinals).value


def extract_duration_nl(text):
    """Convert an english phrase into a number of seconds

    Convert things like:
        "10 minute"
        "2 and a half hours"
        "3 days 8 hours 10 minutes and 49 seconds"
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

    time_units = {
        'microseconds': 0,
        'milliseconds': 0,
        'seconds': 0,
        'minutes': 0,
        'hours': 0,
        'days': 0,
        'weeks': 0
    }

    nl_translations = {
        'microseconds': ["microsecond", "microseconde", "microseconden", "microsecondje", "microsecondjes"],
        'milliseconds': ["millisecond", "milliseconde", "milliseconden", "millisecondje", "millisecondjes"],
        'seconds': ["second", "seconde", "seconden", "secondje", "secondjes"],
        'minutes': ["minuut", "minuten", "minuutje", "minuutjes"],
        'hours': ["uur", "uren", "uurtje", "uurtjes"],
        'days': ["dag", "dagen", "dagje", "dagjes"],
        'weeks': ["week", "weken", "weekje", "weekjes"]
    }

    pattern = r"(?P<value>\d+(?:\.?\d+)?)\s+{unit}"
    text = _convert_words_to_numbers_nl(text)

    for unit in time_units:
        unit_nl_words = nl_translations[unit]
        unit_nl_words.sort(key=len, reverse=True)
        for unit_nl in unit_nl_words:
            unit_pattern = pattern.format(unit=unit_nl)
            matches = re.findall(unit_pattern, text)
            value = sum(map(float, matches))
            time_units[unit] = time_units[unit] + value
            text = re.sub(unit_pattern, '', text)

    text = text.strip()
    duration = timedelta(**time_units) if any(time_units.values()) else None

    return (duration, text)


def extract_datetime_nl(text, anchorDate=None, default_time=None):
    """Convert a human date reference into an exact datetime

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

    The "next" instance of a day or weekend is considered to be no earlier than
    48 hours in the future. On Friday, "next Monday" would be in 3 days.
    On Saturday, "next Monday" would be in 9 days.

    Args:
        text (str): string containing date words
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
            .replace(' de ', ' ').replace(' het ', ' ').replace(' het ', ' ') \
            .replace("paar", "2").replace("eeuwen", "eeuw") \
            .replace("decennia", "decennium") \
            .replace("millennia", "millennium")

        wordList = s.split()
        for idx, word in enumerate(wordList):
            ordinals = ["ste", "de"]
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

    if text == "" or not anchorDate:
        return None

    found = False
    daySpecified = False
    dayOffset = False
    monthOffset = 0
    yearOffset = 0
    today = anchorDate.strftime("%w")
    currentYear = anchorDate.strftime("%Y")
    fromFlag = False
    datestr = ""
    hasYear = False
    timeQualifier = ""

    timeQualifiersAM = ['ochtend']
    timeQualifiersPM = ['middag', 'avond', 'nacht']
    timeQualifiersList = timeQualifiersAM + timeQualifiersPM
    timeQualifierOffsets = [8, 15, 19, 0]
    markers = ['op', 'in', 'om', 'tegen', 'over',
               'deze', 'rond', 'voor', 'van', "binnen"]
    days = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag",
            "zaterdag", "zondag"]
    day_parts = [a + b for a in days for b in timeQualifiersList]
    months = ['januari', 'februari', 'maart', 'april', 'mei', 'juni',
              'juli', 'augustus', 'september', 'oktober', 'november',
              'december']
    recur_markers = days + [d+'en' for d in days] + ['weekeinde', 'werkdag',
                                                     'weekeinden', 'werkdagen']
    months_short = ['jan', 'feb', 'mar', 'apr', 'mei', 'jun', 'jul', 'aug',
                    'sep', 'okt', 'nov', 'dec']
    year_multiples = ["decennium", "eeuw", "millennium"]
    day_multiples = ["dagen", "weken", "maanden", "jaren"]

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

        if word == "nu" and not datestr:
            resultStr = " ".join(words[idx + 1:])
            resultStr = ' '.join(resultStr.split())
            extractedDate = anchorDate.replace(microsecond=0)
            return [extractedDate, resultStr]
        elif wordNext in year_multiples:
            multiplier = None
            if is_numeric(word):
                multiplier = extract_number_nl(word)
            multiplier = multiplier or 1
            multiplier = int(multiplier)
            used += 2
            if wordNext == "decennium":
                yearOffset = multiplier * 10
            elif wordNext == "eeuw":
                yearOffset = multiplier * 100
            elif wordNext == "millennium":
                yearOffset = multiplier * 1000
        # paar
        elif word == "2" and \
                wordNextNext in year_multiples:
            multiplier = 2
            used += 2
            if wordNextNext == "decennia":
                yearOffset = multiplier * 10
            elif wordNextNext == "eeuwen":
                yearOffset = multiplier * 100
            elif wordNextNext == "millennia":
                yearOffset = multiplier * 1000
        elif word == "2" and \
                wordNextNext in day_multiples:
            multiplier = 2
            used += 2
            if wordNextNext == "jaren":
                yearOffset = multiplier
            elif wordNextNext == "maanden":
                monthOffset = multiplier
            elif wordNextNext == "weken":
                dayOffset = multiplier * 7
        elif word in timeQualifiersList:
            timeQualifier = word
        # parse today, tomorrow, day after tomorrow
        elif word == "vandaag" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "morgen" and not fromFlag:
            dayOffset = 1
            used += 1
        elif word == "overmorgen" and not fromFlag:
            dayOffset = 2
            used += 1
            # parse 5 days, 10 weeks, last week, next week
        elif word == "dag" or word == "dagen":
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev)
                start -= 1
                used = 2
        elif word == "week" or word == "weken" and not fromFlag:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            elif wordPrev == "volgende":
                dayOffset = 7
                start -= 1
                used = 2
            elif wordPrev == "vorige":
                dayOffset = -7
                start -= 1
                used = 2
                # parse 10 months, next month, last month
        elif word == "maand" and not fromFlag:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "volgende":
                monthOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "vorige":
                monthOffset = -1
                start -= 1
                used = 2
        # parse 5 years, next year, last year
        elif word == "jaar" and not fromFlag:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "volgend":
                yearOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "vorig":
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
            if wordPrev == "volgende":
                if dayOffset <= 2:
                    dayOffset += 7
                used += 1
                start -= 1
            elif wordPrev == "vorige":
                dayOffset -= 7
                used += 1
                start -= 1
        elif word in day_parts and not fromFlag:
            d = day_parts.index(word) / len(timeQualifiersList)
            dayOffset = (d + 1) - int(today)
            if dayOffset < 0:
                dayOffset += 7
                # parse 15 of July, June 20th, Feb 18, 19 of February
        elif word in months or word in months_short and not fromFlag:
            try:
                m = months.index(word)
            except ValueError:
                m = months_short.index(word)
            used += 1
            datestr = months[m]
            if wordPrev and \
                    (wordPrev[0].isdigit() or (wordPrev == "van" and
                                               wordPrevPrev[0].isdigit())):
                if wordPrev == "van" and wordPrevPrev[0].isdigit():
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
        validFollowups = days + months + months_short
        validFollowups.append("vandaag")
        validFollowups.append("morgen")
        validFollowups.append("volgende")
        validFollowups.append("vorige")
        validFollowups.append("nu")
        if (word == "van" or word == "na") and wordNext in validFollowups:
            used = 2
            fromFlag = True
            if wordNext == "morgen":
                dayOffset += 1
            elif wordNext == "overmorgen":
                dayOffset += 2
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
                if wordNext == "volgende":
                    if dayOffset <= 2:
                        tmpOffset += 7
                    used += 1
                    start -= 1
                elif wordNext == "vorige":
                    tmpOffset -= 7
                    used += 1
                    start -= 1
                dayOffset += tmpOffset
        if used > 0:
            if start - 1 > 0 and words[start - 1] == "deze":
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
        # parse nacht ochtend, middag, avond
        used = 0
        if word.startswith("gister"):
            dayOffset = -1
        elif word.startswith("morgen"):
            dayOffset = 1

        if word.endswith("nacht"):
            if hrAbs is None:
                hrAbs = 0
            used += 1
        elif word.endswith("ochtend"):
            if hrAbs is None:
                hrAbs = 8
            used += 1
        elif word.endswith("middag"):
            if hrAbs is None:
                hrAbs = 15
            used += 1
        elif word.endswith("avond"):
            if hrAbs is None:
                hrAbs = 19
            used += 1

        # "paar" time_unit
        elif word == "2" and \
                wordNextNext in ["uur", "minuten", "seconden"]:
            used += 2
            if wordNextNext == "uur":
                hrOffset = 2
            elif wordNextNext == "minuten":
                minOffset = 2
            elif wordNextNext == "seconden":
                secOffset = 2
        # parse half an hour, quarter hour
        elif word == "uur" and \
                (wordPrev in markers or wordPrevPrev in markers):
            if wordPrev == "half":
                minOffset = 30
            elif wordPrev == "kwartier":
                minOffset = 15
            elif wordPrevPrev == "kwartier":
                minOffset = 15
                if idx > 2 and words[idx - 3] in markers:
                    words[idx - 3] = ""
                    if words[idx - 3] == "deze":
                        daySpecified = True
                words[idx - 2] = ""
            elif wordPrev == "binnen":
                hrOffset = 1
            else:
                hrOffset = 1
            if wordPrevPrev in markers:
                words[idx - 2] = ""
                if wordPrevPrev == "deze":
                    daySpecified = True
            words[idx - 1] = ""
            used += 1
            hrAbs = -1
            minAbs = -1
            # parse 5:00 am, 12:00 p.m., etc
        # parse "over een minuut"
        elif word == "minuut" and wordPrev == "over":
            minOffset = 1
            words[idx - 1] = ""
            used += 1
        # parse "over een seconde"
        elif word == "seconde" and wordPrev == "over":
            secOffset = 1
            words[idx - 1] = ""
            used += 1
        elif word[0].isdigit():
            isTime = True
            strHH = ""
            strMM = ""
            remainder = ""
            wordNextNextNext = words[idx + 3] \
                if idx + 3 < len(words) else ""
            if wordNext == "vannacht" or wordNextNext == "vannacht" or \
                    wordPrev == "vannacht" or wordPrevPrev == "vannacht" or \
                    wordNextNextNext == "vannacht":
                remainder = "pm"
                used += 1
                if wordPrev == "vannacht":
                    words[idx - 1] = ""
                if wordPrevPrev == "vannacht":
                    words[idx - 2] = ""
                if wordNextNext == "vannacht":
                    used += 1
                if wordNextNextNext == "vannacht":
                    used += 1

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

                    elif wordNext == "in" and wordNextNext == "ochtend":
                        remainder = "am"
                        used += 2
                    elif wordNext == "in" and wordNextNext == "middag":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "in" and wordNextNext == "avond":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "'s" and wordNextNext == "ochtends":
                        remainder = "am"
                        used += 2
                    elif wordNext == "'s" and wordNextNext == "middags":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "'s" and wordNextNext == "avonds":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "deze" and wordNextNext == "ochtend":
                        remainder = "am"
                        used = 2
                        daySpecified = True
                    elif wordNext == "deze" and wordNextNext == "middag":
                        remainder = "pm"
                        used = 2
                        daySpecified = True
                    elif wordNext == "deze" and wordNextNext == "avond":
                        remainder = "pm"
                        used = 2
                        daySpecified = True
                    elif wordNext == "'s" and wordNextNext == "nachts":
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
                elif (
                        remainder in recur_markers or
                        wordNext in recur_markers or
                        wordNextNext in recur_markers):
                    # Ex: "7 on mondays" or "3 this friday"
                    # Set strHH so that isTime == True
                    # when am or pm is not specified
                    strHH = strNum
                    used = 1
                else:
                    if (
                            (wordNext == "uren" or wordNext == "uur" or
                             remainder == "uren" or remainder == "uur") and
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

                    elif wordNext == "minuten" or wordNext == "minuut" or \
                            remainder == "minuten" or remainder == "minuut":
                        # "in 10 minutes"
                        minOffset = int(strNum)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif wordNext == "seconden" or wordNext == "seconde" \
                            or remainder == "seconden" or \
                            remainder == "seconde":
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
                        if wordNext == "uur" or remainder == "uur":
                            used += 1
                    elif wordNext and wordNext[0].isdigit():
                        # military time, e.g. "04 38 hours"
                        strHH = strNum
                        strMM = wordNext
                        military = True
                        used += 1
                        if (wordNextNext == "uur" or remainder == "uur"):
                            used += 1
                    elif (
                            wordNext == "" or wordNext == "uur" or
                            (
                                wordNext == "in" and
                                (
                                        wordNextNext == "de" or
                                        wordNextNext == timeQualifier
                                )
                            ) or wordNext == 'vannacht' or
                            wordNextNext == 'vannacht'):

                        strHH = strNum
                        strMM = "00"
                        if wordNext == "uur":
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
                            if timeQualifier in timeQualifiersPM:
                                remainder = "pm"
                                used += 1

                            elif timeQualifier in timeQualifiersAM:
                                remainder = "am"
                                used += 1
                            else:
                                # TODO: Unsure if this is 100% accurate
                                used += 1
                                military = True
                    else:
                        isTime = False
            HH = int(strHH) if strHH else 0
            MM = int(strMM) if strMM else 0
            HH = HH + 12 if remainder == "pm" and HH < 12 else HH
            HH = HH - 12 if remainder == "am" and HH >= 12 else HH

            if (not military and
                    remainder not in ['am', 'pm', 'uren', 'minuten',
                                      "seconde", "seconden",
                                      "uur", "minuut"] and
                    ((not daySpecified) or dayOffset < 1)):
                # ambiguous time, detect whether they mean this evening or
                # the next morning based on whether it has already passed
                if anchorDate.hour < HH or (anchorDate.hour == HH and
                                            anchorDate.minute < MM):
                    pass  # No modification needed
                elif anchorDate.hour < HH + 12:
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

            if wordPrev == "vroeg":
                hrOffset = -1
                words[idx - 1] = ""
                idx -= 1
            elif wordPrev == "laat":
                hrOffset = 1
                words[idx - 1] = ""
                idx -= 1
            if idx > 0 and wordPrev in markers:
                words[idx - 1] = ""
                if wordPrev == "deze":
                    daySpecified = True
            if idx > 1 and wordPrevPrev in markers:
                words[idx - 2] = ""
                if wordPrevPrev == "deze":
                    daySpecified = True

            idx += used - 1
            found = True
    # check that we found a date
    if not date_found():
        return None

    if dayOffset is False:
        dayOffset = 0

    # perform date manipulation

    extractedDate = anchorDate.replace(microsecond=0)

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

        extractedDate = extractedDate.replace(hour=hrAbs,
                                              minute=minAbs)
        if (hrAbs != 0 or minAbs != 0) and datestr == "":
            if not daySpecified and anchorDate > extractedDate:
                extractedDate = extractedDate + relativedelta(days=1)
    if hrOffset != 0:
        extractedDate = extractedDate + relativedelta(hours=hrOffset)
    if minOffset != 0:
        extractedDate = extractedDate + relativedelta(minutes=minOffset)
    if secOffset != 0:
        extractedDate = extractedDate + relativedelta(seconds=secOffset)
    for idx, word in enumerate(words):
        if words[idx] == "en" and \
                words[idx - 1] == "" and words[idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())
    return [extractedDate, resultStr]


def is_fractional_nl(input_str, short_scale=True):
    """This function takes the given text and checks if it is a fraction.

    Args:
        input_str (str): the string to check if fractional
        short_scale (bool): use short scale if True, long scale if False
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction
    """
    fracts = {"heel": 1, "half": 2, "halve": 2, "kwart": 4}
    if short_scale:
        for num in _SHORT_ORDINAL_STRING_NL:
            if num > 2:
                fracts[_SHORT_ORDINAL_STRING_NL[num]] = num
    else:
        for num in _LONG_ORDINAL_STRING_NL:
            if num > 2:
                fracts[_LONG_ORDINAL_STRING_NL[num]] = num

    if input_str.lower() in fracts:
        return 1.0 / fracts[input_str.lower()]
    return False


def extract_numbers_nl(text, short_scale=True, ordinals=False):
    """Takes in a string and extracts a list of numbers.

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
    results = _extract_numbers_with_text_nl(tokenize(text),
                                            short_scale, ordinals)
    return [float(result.value) for result in results]


def normalize_nl(text, remove_articles=True):
    """Dutch string normalization."""

    words = text.split()  # this also removed extra spaces
    normalized = ""
    for word in words:
        if remove_articles and word in _ARTICLES_NL:
            continue

        # Convert numbers into digits, e.g. "two" -> "2"
        textNumbers = ["nul", "een", "twee", "drie", "vier", "vijf", "zes",
                       "zeven", "acht", "negen", "tien", "elf", "twaalf",
                       "dertien", "veertien", "vijftien", "zestien",
                       "zeventien", "achttien", "negentien", "twintig"]

        if word in textNumbers:
            word = str(textNumbers.index(word))

        normalized += " " + word

    return normalized[1:]  # strip the initial space


class DutchNormalizer(Normalizer):
    """ TODO implement language specific normalizer"""
