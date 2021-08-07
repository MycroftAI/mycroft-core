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
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from lingua_franca.lang.parse_common import is_numeric, look_for_fractions, \
    invert_dict, ReplaceableNumber, partition_list, tokenize, Token
from lingua_franca.lang.common_data_pl import _NUM_STRING_PL, \
    _SHORT_SCALE_PL, _SHORT_ORDINAL_PL, _FRACTION_STRING_PL, _TIME_UNITS_CONVERSION, \
    _TIME_UNITS_NORMALIZATION, _MONTHS_TO_EN, _DAYS_TO_EN, _ORDINAL_BASE_PL, \
    _ALT_ORDINALS_PL

import re


def generate_plurals_pl(originals):
    """
    Return a new set or dict containing the plural form of the original values,

    In English this means all with 's' appended to them.

    Args:
        originals set(str) or dict(str, any): values to pluralize

    Returns:
        set(str) or dict(str, any)

    """
    if isinstance(originals, dict):
        result = {key + 'y': value for key, value in originals.items()}
        result = {**result, **{key + 'ów': value for key, value in originals.items()}}
        result = {**result, **{'tysiące': 1000, 'tysięcy': 1000}}

        return result

    result = {value + "y" for value in originals}
    result = result.union({value + "ów" for value in originals})
    result = result.union({'tysiące', 'tysięcy'})

    return result


def generate_fractions_pl(fractions):
    '''Returns a list of all fraction combinations. E.g.:
    trzecia, trzecich, trzecie
    czwarta, czwarte, czwartych

    :param fractions: Existing fractions
    :return: Fractions with add suffixes
    '''

    result = {**fractions}
    for k, v in fractions.items():
        k_no_last = k[:-1]
        result[k_no_last + 'e'] = v
        if k_no_last[-1:] == 'i':
            result[k_no_last + 'ch'] = v
        else:
            result[k_no_last + 'ych'] = v

    for k,v in _SHORT_ORDINAL_PL.items():
        result[v[:-1] + 'a'] = k

    result['jedno'] = 1
    result['czwartego'] = 4

    return result


# negate next number (-2 = 0 - 2)
_NEGATIVES = {"ujemne", "minus"}

# sum the next number (twenty two = 20 + 2)
_SUMS = {'dwadzieścia', '20', 'trzydzieści', '30', 'czterdzieści', '40', 'pięćdziesiąt', '50',
         'sześćdziesiąt', '60', 'siedemdziesiąt', '70', 'osiemdziesiąt', '80', 'dziewięćdziesiąt', '90'}

_MULTIPLIES_SHORT_SCALE_PL = generate_plurals_pl(_SHORT_SCALE_PL.values())

# split sentence parse separately and sum ( 2 and a half = 2 + 0.5 )
_FRACTION_MARKER = {'i'}

# decimal marker ( 1 point 5 = 1 + 0.5)
_DECIMAL_MARKER = {'kropka', 'przecinek'}

_STRING_NUM_PL = invert_dict(_NUM_STRING_PL)
_STRING_NUM_PL.update(generate_plurals_pl(_STRING_NUM_PL))
_STRING_NUM_PL.update({
    'pół': 0.5,
    'połówka': 0.5,
    'połowa': 0.5,
})

_STRING_SHORT_ORDINAL_PL = invert_dict(_SHORT_ORDINAL_PL)

_REV_FRACTITONS = generate_fractions_pl(invert_dict(_FRACTION_STRING_PL))


def _convert_words_to_numbers_pl(text, short_scale=True, ordinals=False):
    """
    Convert words in a string into their equivalent numbers.
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
        _extract_numbers_with_text_pl(tokens, short_scale, ordinals)
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


def _extract_numbers_with_text_pl(tokens, short_scale=True,
                                  ordinals=False, fractional_numbers=True):
    """
    Extract all numbers from a list of Tokens, with the words that
    represent them.

    Args:
        [Token]: The tokens to parse.
        short_scale bool: True if short scale numbers should be used, False for
                          long scale. True by default.
        ordinals bool: True if ordinal words (first, second, third, etc) should
                       be parsed.
        fractional_numbers bool: True if we should look for fractions and
                                 decimals.

    Returns:
        [ReplaceableNumber]: A list of tuples, each containing a number and a
                         string.

    """
    placeholder = "<placeholder>"  # inserted to maintain correct indices
    results = []
    while True:
        to_replace = \
            _extract_number_with_text_pl(tokens, short_scale,
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


def _extract_number_with_text_pl(tokens, short_scale=True,
                                 ordinals=False, fractional_numbers=True):
    """
    This function extracts a number from a list of Tokens.

    Args:
        tokens str: the string to normalize
        short_scale (bool): use short scale if True, long scale if False
        ordinals (bool): consider ordinal numbers, third=3 instead of 1/3
        fractional_numbers (bool): True if we should look for fractions and
                                   decimals.
    Returns:
        ReplaceableNumber

    """
    number, tokens = \
        _extract_number_with_text_pl_helper(tokens, short_scale,
                                            ordinals, fractional_numbers)
    return ReplaceableNumber(number, tokens)


def _extract_number_with_text_pl_helper(tokens,
                                        short_scale=True, ordinals=False,
                                        fractional_numbers=True):
    """
    Helper for _extract_number_with_text_en.

    This contains the real logic for parsing, but produces
    a result that needs a little cleaning (specific, it may
    contain leading articles that can be trimmed off).

    Args:
        tokens [Token]:
        short_scale boolean:
        ordinals boolean:
        fractional_numbers boolean:

    Returns:
        int or float, [Tokens]

    """
    if fractional_numbers:
        fraction, fraction_text = \
            _extract_fraction_with_text_pl(tokens, short_scale, ordinals)
        if fraction:
            return fraction, fraction_text

        decimal, decimal_text = \
            _extract_decimal_with_text_pl(tokens, short_scale, ordinals)
        if decimal:
            return decimal, decimal_text

    return _extract_whole_number_with_text_pl(tokens, short_scale, ordinals)


def _extract_fraction_with_text_pl(tokens, short_scale, ordinals):
    """
    Extract fraction numbers from a string.

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
    for c in _FRACTION_MARKER:
        partitions = partition_list(tokens, lambda t: t.word == c)

        if len(partitions) == 3:
            numbers1 = \
                _extract_numbers_with_text_pl(partitions[0], short_scale,
                                              ordinals, fractional_numbers=False)
            numbers2 = \
                _extract_numbers_with_text_pl(partitions[2], short_scale,
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


def _extract_decimal_with_text_pl(tokens, short_scale, ordinals):
    """
    Extract decimal numbers from a string.

    This function handles text such as '2 point 5'.

    Notes:
        While this is a helper for extractnumber_en, it also depends on
        extractnumber_en, to parse out the components of the decimal.

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
    for c in _DECIMAL_MARKER:
        partitions = partition_list(tokens, lambda t: t.word == c)

        if len(partitions) == 3:
            numbers1 = \
                _extract_numbers_with_text_pl(partitions[0], short_scale,
                                              ordinals, fractional_numbers=False)
            numbers2 = \
                _extract_numbers_with_text_pl(partitions[2], short_scale,
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


def _extract_whole_number_with_text_pl(tokens, short_scale, ordinals):
    """
    Handle numbers not handled by the decimal or fraction functions. This is
    generally whole numbers. Note that phrases such as "one half" will be
    handled by this function, while "one and a half" are handled by the
    fraction function.

    Args:
        tokens [Token]:
        short_scale boolean:
        ordinals boolean:

    Returns:
        int or float, [Tokens]
        The value parsed, and tokens that it corresponds to.

    """
    multiplies, string_num_ordinal, string_num_scale = \
        _initialize_number_data(short_scale)

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

        prev_word = tokens[idx - 1].word if idx > 0 else ""
        next_word = tokens[idx + 1].word if idx + 1 < len(tokens) else ""

        if is_numeric(word[:-1]) and word.endswith('.'):
            # explicit ordinals, 1., 2., 3., 4.... N.
            word = word[:-1]

        word = normalize_word_pl(word)

        if word not in string_num_scale and \
                word not in _STRING_NUM_PL and \
                word not in _SUMS and \
                word not in multiplies and \
                not (ordinals and word in string_num_ordinal) and \
                not is_numeric(word) and \
                not isFractional_pl(word) and \
                not look_for_fractions(word.split('/')):
            words_only = [token.word for token in number_words]
            if number_words and not all([w in _NEGATIVES for w in words_only]):
                break
            else:
                number_words = []
                continue
        elif word not in multiplies \
                and prev_word not in multiplies \
                and prev_word not in _SHORT_SCALE_PL.values() \
                and prev_word not in _SUMS \
                and not (ordinals and prev_word in string_num_ordinal) \
                and prev_word not in _NEGATIVES:
            number_words = [token]
        elif prev_word in _SUMS and word in _SUMS:
            number_words = [token]
        else:
            number_words.append(token)

        # is this word already a number ?
        if is_numeric(word):
            if word.isdigit():  # doesn't work with decimals
                val = int(word)
            else:
                val = float(word)
            current_val = val

        # is this word the name of a number ?
        if word in _STRING_NUM_PL:
            val = _STRING_NUM_PL.get(word)
            current_val = val
        elif word in string_num_scale:
            val = string_num_scale.get(word)
            current_val = val
        elif ordinals and word in string_num_ordinal:
            val = string_num_ordinal[word]
            current_val = val

        if word in multiplies:
            if not prev_val:
                prev_val = 1
            val = prev_val * val
            prev_val = None

        # is the prev word a number and should we sum it?
        # twenty two, fifty six
        if prev_val:
            if (prev_word in string_num_ordinal and val and val < prev_val) or \
                    (prev_word in _STRING_NUM_PL and val and val < prev_val and val // 10 != prev_val // 10) or \
                    all([prev_word in multiplies, val < prev_val if prev_val else False]):
                val += prev_val

        if next_word in multiplies:
            prev_val = val
            continue

        # is this a spoken fraction?
        # half cup
        if val is False:
            val = isFractional_pl(word)
            current_val = val

        # 2 fifths
        if not ordinals:
            next_val = isFractional_pl(next_word)
            if next_val:
                if not val:
                    val = 1
                val *= next_val
                number_words.append(tokens[idx + 1])

        # is this a negative number?
        if val and prev_word and prev_word in _NEGATIVES:
            val = 0 - val

        if next_word in _STRING_NUM_PL:
            prev_val = val

        # let's make sure it isn't a fraction
        if not val:
            # look for fractions like "2/3"
            aPieces = word.split('/')
            if look_for_fractions(aPieces):
                val = float(aPieces[0]) / float(aPieces[1])
                number_words.append(tokens[idx + 1])
        else:
            if all([
                    prev_word in _SUMS,
                    word not in _SUMS,
                    word not in multiplies,
                    current_val >= 10]):
                # Backtrack - we've got numbers we can't sum.
                number_words.pop()
                val = prev_val
                break
            prev_val = val

            if word in multiplies and next_word not in multiplies:
                # handle long numbers
                # six hundred sixty six
                # two million five hundred thousand
                #
                # This logic is somewhat complex, and warrants
                # extensive documentation for the next coder's sake.
                #
                # The current word is a power of ten. `current_val` is
                # its integer value. `val` is our working sum
                # (above, when `current_val` is 1 million, `val` is
                # 2 million.)
                #
                # We have a dict `string_num_scale` containing [value, word]
                # pairs for "all" powers of ten: string_num_scale[10] == "ten.
                #
                # We need go over the rest of the tokens, looking for other
                # powers of ten. If we find one, we compare it with the current
                # value, to see if it's smaller than the current power of ten.
                #
                # Numbers which are not powers of ten will be passed over.
                #
                # If all the remaining powers of ten are smaller than our
                # current value, we can set the current value aside for later,
                # and begin extracting another portion of our final result.
                # For example, suppose we have the following string.
                # The current word is "million".`val` is 9000000.
                # `current_val` is 1000000.
                #
                #    "nine **million** nine *hundred* seven **thousand**
                #     six *hundred* fifty seven"
                #
                # Iterating over the rest of the string, the current
                # value is larger than all remaining powers of ten.
                #
                # The if statement passes, and nine million (9000000)
                # is appended to `to_sum`.
                #
                # The main variables are reset, and the main loop begins
                # assembling another number, which will also be appended
                # under the same conditions.
                #
                # By the end of the main loop, to_sum will be a list of each
                # "place" from 100 up: [9000000, 907000, 600]
                #
                # The final three digits will be added to the sum of that list
                # at the end of the main loop, to produce the extracted number:
                #
                #    sum([9000000, 907000, 600]) + 57
                # == 9,000,000 + 907,000 + 600 + 57
                # == 9,907,657
                #
                # >>> foo = "nine million nine hundred seven thousand six
                #            hundred fifty seven"
                # >>> extract_number(foo)
                # 9907657

                time_to_sum = True
                for other_token in tokens[idx+1:]:
                    if other_token.word in multiplies:
                        if string_num_scale[other_token.word] >= current_val:
                            time_to_sum = False
                        else:
                            continue
                    if not time_to_sum:
                        break
                if time_to_sum:
                    to_sum.append(val)
                    val = 0
                    prev_val = 0

    if val is not None and to_sum:
        val += sum(to_sum)

    return val, number_words


def _initialize_number_data(short_scale):
    """
    Generate dictionaries of words to numbers, based on scale.

    This is a helper function for _extract_whole_number.

    Args:
        short_scale boolean:

    Returns:
        (set(str), dict(str, number), dict(str, number))
        multiplies, string_num_ordinal, string_num_scale

    """
    multiplies = _MULTIPLIES_SHORT_SCALE_PL

    string_num_scale = invert_dict(_SHORT_SCALE_PL)
    string_num_scale.update(generate_plurals_pl(string_num_scale))
    return multiplies, _STRING_SHORT_ORDINAL_PL, string_num_scale


def extract_number_pl(text, short_scale=True, ordinals=False):
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
    return _extract_number_with_text_pl(tokenize(text.lower()),
                                        True, ordinals).value


def extract_duration_pl(text):
    """
    Convert an english phrase into a number of seconds

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
        'microseconds': None,
        'milliseconds': None,
        'seconds': None,
        'minutes': None,
        'hours': None,
        'days': None,
        'weeks': None
    }

    pattern = r"(?P<value>\d+(?:\.?\d+)?)(?:\s+|\-){unit}[ayeę]?"
    text = _convert_words_to_numbers_pl(text)

    for unit in _TIME_UNITS_CONVERSION:
        unit_pattern = pattern.format(unit=unit)
        matches = re.findall(unit_pattern, text)
        value = sum(map(float, matches))
        unit_en = _TIME_UNITS_CONVERSION.get(unit)
        if time_units[unit_en] is None or time_units.get(unit_en) == 0:
            time_units[unit_en] = value
        text = re.sub(unit_pattern, '', text)

    text = text.strip()
    duration = timedelta(**time_units) if any(time_units.values()) else None

    return (duration, text)


def extract_datetime_pl(string, dateNow=None, default_time=None):
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

    The "next" instance of a day or weekend is considered to be no earlier than
    48 hours in the future. On Friday, "next Monday" would be in 3 days.
    On Saturday, "next Monday" would be in 9 days.

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
            .replace("para", "2")

        wordList = s.split()
        for idx, word in enumerate(wordList):
            ordinals = ["ci", "szy", "gi"]
            if word[0].isdigit():
                for ordinal in ordinals:
                    if ordinal in word:
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

    timeQualifiersAM = ['rano']
    timeQualifiersPM = ['wieczór', 'w nocy']
    timeQualifiersList = set(timeQualifiersAM + timeQualifiersPM)
    markers = ['na', 'w', 'we', 'na', 'przez', 'ten', 'około', 'dla', 'o', "pomiędzy", 'za', 'do']
    days = list(_DAYS_TO_EN.keys())
    recur_markers = days + ['weekend', 'weekendy']
    monthsShort = ['sty', 'lut', 'mar', 'kwi', 'maj', 'cze', 'lip', 'sie',
                   'wrz', 'paź', 'lis', 'gru']
    year_multiples = ['dekada', 'wiek', 'milenia']

    words = clean_string(string)

    for idx, word in enumerate(words):
        if word == "":
            continue
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""

        # this isn't in clean string because I don't want to save back to words
        start = idx
        used = 0
        # save timequalifier for later
        if word == 'w' and wordNext == 'tę':
            used += 2
        if word == "temu" and dayOffset:
            dayOffset = - dayOffset
            used += 1
        if word == "teraz" and not datestr:
            resultStr = " ".join(words[idx + 1:])
            resultStr = ' '.join(resultStr.split())
            extractedDate = dateNow.replace(microsecond=0)
            return [extractedDate, resultStr]
        elif wordNext in year_multiples:
            multiplier = None
            if is_numeric(word):
                multiplier = extract_number_pl(word)
            multiplier = multiplier or 1
            multiplier = int(multiplier)
            used += 2
            if _TIME_UNITS_NORMALIZATION.get(wordNext) == "dekada":
                yearOffset = multiplier * 10
            elif _TIME_UNITS_NORMALIZATION.get(wordNext) == "wiek":
                yearOffset = multiplier * 100
            elif _TIME_UNITS_NORMALIZATION.get(wordNext) == "milenia":
                yearOffset = multiplier * 1000
        elif word in timeQualifiersList:
            timeQualifier = word
        # parse today, tomorrow, day after tomorrow
        elif word == "dzisiaj" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "jutro" and not fromFlag:
            dayOffset = 1
            used += 1
        elif word == "przedwczoraj" and not fromFlag:
            dayOffset = -2
            used += 1
        elif word == "wczoraj" and not fromFlag:
            dayOffset = -1
            used += 1
        elif word == "pojutrze" and not fromFlag:
            dayOffset = 2
            used = 1
        elif word == "dzień" and wordNext != 'robocze':
            if wordPrev and wordPrev[0].isdigit():
                dayOffset += int(wordPrev)
                start -= 1
                used = 2
        elif word == "tydzień" and not fromFlag and wordPrev:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            elif wordPrev == "następny":
                dayOffset = 7
                start -= 1
                used = 2
            elif wordPrev == "poprzedni" or wordPrev == 'ostatni':
                dayOffset = -7
                start -= 1
                used = 2
                # parse 10 months, next month, last month
        elif word == "miesiąc" and not fromFlag and wordPrev:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "następny":
                monthOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "poprzedni" or wordPrev == 'ostatni':
                monthOffset = -1
                start -= 1
                used = 2
        # parse 5 years, next year, last year
        elif word == "rok" and not fromFlag and wordPrev:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "następny":
                yearOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "poprzedni" or wordPrev == 'ostatni':
                yearOffset = -1
                start -= 1
                used = 2
        # parse Monday, Tuesday, etc., and next Monday,
        # last Tuesday, etc.
        elif word in days and not fromFlag:
            d = _DAYS_TO_EN.get(word)
            dayOffset = (d + 1) - int(today)
            used = 1
            if dayOffset < 0:
                dayOffset += 7
            if wordPrev == "następny":
                if dayOffset <= 2:
                    dayOffset += 7
                used += 1
                start -= 1
            elif wordPrev == "poprzedni" or wordPrev == 'ostatni':
                dayOffset -= 7
                used += 1
                start -= 1
                # parse 15 of July, June 20th, Feb 18, 19 of February
        elif word in _MONTHS_TO_EN or word in monthsShort and not fromFlag:
            used += 1
            datestr = _MONTHS_TO_EN[word]
            if wordPrev and wordPrev[0].isdigit():
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
        validFollowups = days + list(_MONTHS_TO_EN.keys()) + monthsShort
        validFollowups.append("dzisiaj")
        validFollowups.append("jutro")
        validFollowups.append("wczoraj")
        validFollowups.append("następny")
        validFollowups.append("poprzedni")
        validFollowups.append('ostatni')
        validFollowups.append("teraz")
        validFollowups.append("tego")
        if (word == "od" or word == "po") and wordNext in validFollowups:
            used = 2
            fromFlag = True
            if wordNext == "jutro":
                dayOffset += 1
            elif wordNext == "wczoraj":
                dayOffset -= 1
            elif wordNext in days:
                d = _DAYS_TO_EN.get(wordNext)
                tmpOffset = (d + 1) - int(today)
                used = 2
                if tmpOffset < 0:
                    tmpOffset += 7
                dayOffset += tmpOffset
            elif wordNextNext and wordNextNext in days:
                d = _DAYS_TO_EN.get(wordNextNext)
                tmpOffset = (d + 1) - int(today)
                used = 3
                if wordNext == "następny":
                    if dayOffset <= 2:
                        tmpOffset += 7
                    used += 1
                    start -= 1
                elif wordNext == "poprzedni" or wordNext == 'ostatni':
                    tmpOffset -= 7
                    used += 1
                    start -= 1
                dayOffset += tmpOffset
        if used > 0:
            if start - 1 > 0 and words[start - 1] == "ten": # this
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
        if word == "południe":
            hrAbs = 12
            used += 1
        elif word == "północ" or word == 'północy':
            hrAbs = 0
            used += 1
        elif word == "rano":
            if hrAbs is None:
                hrAbs = 8
            used += 1
        elif word == "po" and wordNext == "południu":
            if hrAbs is None:
                hrAbs = 15
            used += 2
        elif word == "wieczór" or word == 'wieczorem':
            if hrAbs is None:
                hrAbs = 19
            used += 1
        elif word == "nocy":
            if hrAbs is None:
                hrAbs = 22
            used += 1
        # parse half an hour, quarter hour
        elif word == "godzina" and (wordPrev.isdigit() or wordPrev in markers or wordPrevPrev in markers):
            if wordPrev == "pół":
                minOffset = 30
            else:
                hrOffset = 1
            if wordPrevPrev in markers:
                words[idx - 2] = ""
                if wordPrevPrev == "dzisiaj":
                    daySpecified = True
            words[idx - 1] = ""
            used += 1
            hrAbs = -1
            minAbs = -1
            # parse 5:00 am, 12:00 p.m., etc
        # parse in a minute
        elif word == "minuta" and (wordPrev.isdigit() or wordPrev in markers):
            minOffset = 1
            words[idx - 1] = ""
            used += 1
        # parse in a second
        elif word == "sekunda" and (wordPrev.isdigit() or wordPrev in markers):
            secOffset = 1
            words[idx - 1] = ""
            used += 1
        elif word[0].isdigit():
            isTime = True
            strHH = ""
            strMM = ""
            remainder = ""
            if wordNext == "wieczorem" or wordPrev == "wieczorem" or \
                wordNext == 'wieczór' or wordPrev == 'wieczór' or \
                    (wordNext == 'po' and wordNextNext == 'południu'):
                remainder = "pm"
                used += 2 if wordNext == 'po' else 1
                if wordPrev == "wieczorem" or wordPrev == 'wieczór':
                    words[idx - 1] = ""

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
                    if wordNext == "rano":
                        remainder = "am"
                        used += 1
                    elif wordNext == "po" and wordNextNext == "południu":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "wieczorem":
                        remainder = "pm"
                        used += 1
                    elif wordNext == "rano":
                        remainder = "am"
                        used += 1
                    elif wordNext == "w" and wordNextNext == "nocy":
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
                wordNextNextNext = words[idx + 3] \
                    if idx + 3 < len(words) else ""
                for i in range(length):
                    if word[i].isdigit():
                        strNum += word[i]
                    else:
                        remainder += word[i]

                if remainder == "":
                    remainder = wordNext.replace(".", "").lstrip().rstrip()
                if (
                        remainder == "pm" or
                        (word[0].isdigit() and (wordNext == 'wieczorem' or wordNext == 'wieczór')) or
                        (word[0].isdigit() and wordNext == 'po' and wordNextNext == 'południu') or
                        (word[0].isdigit() and wordNext == 'w' and wordNextNext == 'nocy')):
                    strHH = strNum
                    remainder = "pm"
                    used = 2 if wordNext in ['po', 'w'] else 1
                elif (
                        remainder == "am" or
                        (word[0].isdigit() and wordNext == 'rano')):
                    strHH = strNum
                    remainder = "am"
                    used = 1
                elif (
                        remainder in recur_markers or
                        wordNext in recur_markers or
                        wordNextNext in recur_markers or (
                            wordNext == 'w' and wordNextNext == 'dzień' and
                            wordNextNextNext == 'robocze'
                        )):
                    # Ex: "7 on mondays" or "3 this friday"
                    # Set strHH so that isTime == True
                    # when am or pm is not specified
                    strHH = strNum
                    used = 1
                else:
                    if _TIME_UNITS_NORMALIZATION.get(wordNext) == "godzina" or \
                            _TIME_UNITS_NORMALIZATION.get(remainder) == "godzina":
                        # "in 10 hours"
                        hrOffset = int(strNum)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif _TIME_UNITS_NORMALIZATION.get(wordNext) == "minuta" or \
                            _TIME_UNITS_NORMALIZATION.get(remainder) == "minuta":
                        # "in 10 minutes"
                        minOffset = int(strNum)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif _TIME_UNITS_NORMALIZATION.get(wordNext) == "sekunda" \
                            or _TIME_UNITS_NORMALIZATION.get(remainder) == "sekunda":
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
                        if _TIME_UNITS_NORMALIZATION.get(wordNext) == "godzina" or \
                                _TIME_UNITS_NORMALIZATION.get(remainder) == "godzina":
                            used += 1
                    elif wordNext and wordNext[0].isdigit():
                        # military time, e.g. "04 38 hours"
                        strHH = strNum
                        strMM = wordNext
                        military = True
                        used += 1
                    elif (
                            wordNext == "" or wordNext == "w" or wordNext == 'nocy' or
                            wordNextNext == 'nocy'):
                        strHH = strNum
                        strMM = "00"

                        if wordNext == "za" or wordNextNext == "za":
                            used += (1 if wordNext == "za" else 2)
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
                    remainder not in ['am', 'pm'] and
                    remainder not in _TIME_UNITS_NORMALIZATION and
                    ((not daySpecified) or 0 <= dayOffset < 1)):

                # ambiguous time, detect whether they mean this evening or
                # the next morning based on whether it has already passed
                if dateNow.hour < HH or (dateNow.hour == HH and
                                         dateNow.minute < MM):
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

            if wordPrev == "rano":
                hrOffset = -1
                words[idx - 1] = ""
                idx -= 1
            elif wordPrev == "wieczorem":
                hrOffset = 1
                words[idx - 1] = ""
                idx -= 1
            if idx > 0 and wordPrev in markers:
                words[idx - 1] = ""
                if wordPrev == "najbliższą":
                    daySpecified = True
            if idx > 1 and wordPrevPrev in markers:
                words[idx - 2] = ""
                if wordPrevPrev == "najbliższą":
                    daySpecified = True

            idx += used - 1
            found = True
    # check that we found a date
    if not date_found():
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
        if words[idx] == "i" and \
                words[idx - 1] == "" and words[idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())
    return [extractedDate, resultStr]


def isFractional_pl(input_str, short_scale=True):
    """
    This function takes the given text and checks if it is a fraction.

    Args:
        input_str (str): the string to check if fractional
        short_scale (bool): use short scale if True, long scale if False
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    lower_input = input_str.lower()
    if lower_input in _REV_FRACTITONS:
        return 1.0 / _REV_FRACTITONS[lower_input]

    return False


def extract_numbers_pl(text, short_scale=True, ordinals=False):
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
    results = _extract_numbers_with_text_pl(tokenize(text),
                                            short_scale, ordinals)
    return [float(result.value) for result in results]


def normalize_word_pl(word):
    if word.startswith('jedn'):
        suffix = 'ą', 'ej', 'ym'
        if word.endswith(suffix):
            return 'jedna'
    if word == 'dwie':
        return 'dwa'

    return word


def normalize_pl(text, remove_articles=True):
    """ Polish string normalization """

    words = text.split()  # this also removed extra spaces
    normalized = ""
    for word in words:
        if remove_articles and word in ["i"]:
            continue

        if word in _TIME_UNITS_NORMALIZATION:
            word = _TIME_UNITS_NORMALIZATION[word]

        if word in _REV_FRACTITONS:
            word = str(_REV_FRACTITONS[word])

        if word in _ORDINAL_BASE_PL.values():
            word = str(list(_ORDINAL_BASE_PL.keys())[list(_ORDINAL_BASE_PL.values()).index(word)])

        if word in _NUM_STRING_PL.values():
            word = str(list(_NUM_STRING_PL.keys())[list(_NUM_STRING_PL.values()).index(word)])

        if word in _ALT_ORDINALS_PL.values():
            word = str(list(_ALT_ORDINALS_PL.keys())[list(_ALT_ORDINALS_PL.values()).index(word)])

        if word == 'następną' or word == 'następna' or word == 'następnym' or word == 'następnej':
            word = 'następny'
        elif word == 'ostatnią' or word == 'ostatnia' or word == 'ostatnim' or word == 'ostatniej' or \
            word == 'poprzednią' or word == 'poprzednia' or word == 'poprzednim' or word == 'poprzedniej':
            word = 'poprzedni'
        elif word == 'jutra' or word == 'jutrze':
            word = 'jutro'
        elif word == 'wieczorem':
            word = 'wieczór'
        elif word == 'poranne':
            word = 'rano'

        normalized += " " + word

    return normalized[1:]  # strip the initial space
