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
    invert_dict, ReplaceableNumber, partition_list, tokenize, Token, Normalizer
from lingua_franca.lang.common_data_cs import _NUM_STRING_CS, \
    _LONG_ORDINAL_CS, _LONG_SCALE_CS, _SHORT_SCALE_CS, _SHORT_ORDINAL_CS, \
    _FRACTION_STRING_CS, _MONTHS_CONVERSION, _MONTHS_CZECH, _TIME_UNITS_CONVERSION, \
    _ORDINAL_BASE_CS  # _ARTICLES_CS

import re
import json
from lingua_franca import resolve_resource_file
from lingua_franca.time import now_local


def generate_plurals_cs(originals):
    """
    Return a new set or dict containing the plural form of the original values,

    In English this means all with 's' appended to them.

    Args:
        originals set(str) or dict(str, any): values to pluralize

    Returns:
        set(str) or dict(str, any)

    """
    if isinstance(originals, dict):
        return {key + 'ý': value for key, value in originals.items()}
    return {value + "ý" for value in originals}


# negate next number (-2 = 0 - 2)
_NEGATIVES = {"záporné", "mínus"}

# sum the next number (twenty two = 20 + 2)
_SUMS = {'dvacet', '20', 'třicet', '30', 'čtyřicet', '40', 'padesát', '50',
         'šedesát', '60', 'sedmdesát', '70', 'osmdesát', '80', 'devadesát', '90'}

_MULTIPLIES_LONG_SCALE_CS = set(_LONG_SCALE_CS.values()) | \
    generate_plurals_cs(_LONG_SCALE_CS.values())

_MULTIPLIES_SHORT_SCALE_CS = set(_SHORT_SCALE_CS.values()) | \
    generate_plurals_cs(_SHORT_SCALE_CS.values())

# split sentence parse separately and sum ( 2 and a half = 2 + 0.5 )
_FRACTION_MARKER = {"a"}

# decimal marker ( 1 point 5 = 1 + 0.5)
_DECIMAL_MARKER = {"bod", "tečka", "čárka", "celá"}

_STRING_NUM_CS = invert_dict(_NUM_STRING_CS)
_STRING_NUM_CS.update(generate_plurals_cs(_STRING_NUM_CS))
_STRING_NUM_CS.update({
    "polovina": 0.5,
    "půlka": 0.5,
    "půl": 0.5,
    "jeden": 1,
    "dvojice": 2,
    "dvoje": 2
})

_STRING_SHORT_ORDINAL_CS = invert_dict(_SHORT_ORDINAL_CS)
_STRING_LONG_ORDINAL_CS = invert_dict(_LONG_ORDINAL_CS)


def _convert_words_to_numbers_cs(text, short_scale=True, ordinals=False):
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
        _extract_numbers_with_text_cs(tokens, short_scale, ordinals)
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


def _extract_numbers_with_text_cs(tokens, short_scale=True,
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
            _extract_number_with_text_cs(tokens, short_scale,
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


def _extract_number_with_text_cs(tokens, short_scale=True,
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
        _extract_number_with_text_cs_helper(tokens, short_scale,
                                            ordinals, fractional_numbers)
    # while tokens and tokens[0].word in _ARTICLES_CS:
    #    tokens.pop(0)
    return ReplaceableNumber(number, tokens)


def _extract_number_with_text_cs_helper(tokens,
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
            _extract_fraction_with_text_cs(tokens, short_scale, ordinals)
        if fraction:
            return fraction, fraction_text

        decimal, decimal_text = \
            _extract_decimal_with_text_cs(tokens, short_scale, ordinals)
        if decimal:
            return decimal, decimal_text

    return _extract_whole_number_with_text_cs(tokens, short_scale, ordinals)


def _extract_fraction_with_text_cs(tokens, short_scale, ordinals):
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
                _extract_numbers_with_text_cs(partitions[0], short_scale,
                                              ordinals, fractional_numbers=False)
            numbers2 = \
                _extract_numbers_with_text_cs(partitions[2], short_scale,
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


def _extract_decimal_with_text_cs(tokens, short_scale, ordinals):
    """
    Extract decimal numbers from a string.

    This function handles text such as '2 point 5'.

    Notes:
        While this is a helper for extract_number_xx, it also depends on
        extract_number_xx, to parse out the components of the decimal.

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
                _extract_numbers_with_text_cs(partitions[0], short_scale,
                                              ordinals, fractional_numbers=False)
            numbers2 = \
                _extract_numbers_with_text_cs(partitions[2], short_scale,
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


def _extract_whole_number_with_text_cs(tokens, short_scale, ordinals):
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
        # if word in _ARTICLES_CS or word in _NEGATIVES:
        if word in word in _NEGATIVES:
            number_words.append(token)
            continue

        prev_word = tokens[idx - 1].word if idx > 0 else ""
        next_word = tokens[idx + 1].word if idx + 1 < len(tokens) else ""

        # In czech we do no use suffix (1st,2nd,..) but use point instead (1.,2.,..)
        if is_numeric(word[:-1]) and \
                (word.endswith(".")):

            # explicit ordinals, 1st, 2nd, 3rd, 4th.... Nth
            word = word[:-1]

            # handle nth one
        #    if next_word == "one":
            # would return 1 instead otherwise
        #        tokens[idx + 1] = Token("", idx)
        #        next_word = ""

        # Normalize Czech inflection of numbers(jedna,jeden,jedno,...)
        if not ordinals:
            word = _text_cs_inflection_normalize(word, 1)

        if word not in string_num_scale and \
                word not in _STRING_NUM_CS and \
                word not in _SUMS and \
                word not in multiplies and \
                not (ordinals and word in string_num_ordinal) and \
                not is_numeric(word) and \
                not isFractional_cs(word, short_scale=short_scale) and \
                not look_for_fractions(word.split('/')):
            words_only = [token.word for token in number_words]
            # if number_words and not all([w in _ARTICLES_CS |
            #                             _NEGATIVES for w in words_only]):
            if number_words and not all([w in _NEGATIVES for w in words_only]):
                break
            else:
                number_words = []
                continue
        elif word not in multiplies \
                and prev_word not in multiplies \
                and prev_word not in _SUMS \
                and not (ordinals and prev_word in string_num_ordinal) \
                and prev_word not in _NEGATIVES:  # \
            # and prev_word not in _ARTICLES_CS:
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
        if word in _STRING_NUM_CS:
            val = _STRING_NUM_CS.get(word)
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
        if (prev_word in _SUMS and val and val < 10) or all([prev_word in
                                                             multiplies,
                                                             val < prev_val if prev_val else False]):
            val = prev_val + val

        # For Czech only: If Ordinal previous number will be also in ordinal number format
        # dvacátý první = twentieth first
        if (prev_word in string_num_ordinal and val and val < 10) or all([prev_word in
                                                                          multiplies,
                                                                          val < prev_val if prev_val else False]):
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
            val = isFractional_cs(word, short_scale=short_scale)
            current_val = val

        # 2 fifths
        if not ordinals:
            next_val = isFractional_cs(next_word, short_scale=short_scale)
            if next_val:
                if not val:
                    val = 1
                val = val * next_val
                number_words.append(tokens[idx + 1])

        # is this a negative number?
        if val and prev_word and prev_word in _NEGATIVES:
            val = 0 - val

        # let's make sure it isn't a fraction
        if not val:
            # look for fractions like "2/3"
            aPieces = word.split('/')
            if look_for_fractions(aPieces):
                val = float(aPieces[0]) / float(aPieces[1])
                current_val = val

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
    multiplies = _MULTIPLIES_SHORT_SCALE_CS if short_scale \
        else _MULTIPLIES_LONG_SCALE_CS

    string_num_ordinal_cs = _STRING_SHORT_ORDINAL_CS if short_scale \
        else _STRING_LONG_ORDINAL_CS

    string_num_scale_cs = _SHORT_SCALE_CS if short_scale else _LONG_SCALE_CS
    string_num_scale_cs = invert_dict(string_num_scale_cs)
    string_num_scale_cs.update(generate_plurals_cs(string_num_scale_cs))
    return multiplies, string_num_ordinal_cs, string_num_scale_cs


def extract_number_cs(text, short_scale=True, ordinals=False):
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
    return _extract_number_with_text_cs(tokenize(text.lower()),
                                        short_scale, ordinals).value


def extract_duration_cs(text):
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

    # Czech inflection for time: minuta,minuty,minut - safe to use minut as pattern
    # For day: den, dny, dnů - short patern not applicable, list all

    time_units = {
        'microseconds': 0,
        'milliseconds': 0,
        'seconds': 0,
        'minutes': 0,
        'hours': 0,
        'days': 0,
        'weeks': 0
    }

    pattern = r"(?P<value>\d+(?:\.?\d+)?)(?:\s+|\-){unit}[ay]?"
    text = _convert_words_to_numbers_cs(text)

    for (unit_cs, unit_en) in _TIME_UNITS_CONVERSION.items():
        unit_pattern = pattern.format(unit=unit_cs)

        def repl(match):
            time_units[unit_en] += float(match.group(1))
            return ''
        text = re.sub(unit_pattern, repl, text)

    text = text.strip()
    duration = timedelta(**time_units) if any(time_units.values()) else None

    return (duration, text)


def extract_datetime_cs(text, anchorDate=None, default_time=None):
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
        text (str): string containing date words
        anchorDate (datetime): A reference date/time for "tommorrow", etc
        default_time (time): Time to set if no time was found in the string

    Returns:
        [datetime, str]: An array containing the datetime and the remaining
                         text not consumed in the parsing, or None if no
                         date or time related text was found.
    """

    def clean_string(s):
        # clean unneeded punctuation and capitalization among other things.
        # Normalize czech inflection
        s = s.lower().replace('?', '').replace('.', '').replace(',', '') \
            .replace("dvoje", "2").replace("dvojice", "2") \
            .replace("dnes večer", "večer").replace("dnes v noci", "noci")  # \
        # .replace("tento večer", "večer")
        # .replace(' the ', ' ').replace(' a ', ' ').replace(' an ', ' ') \
        # .replace("o' clock", "o'clock").replace("o clock", "o'clock") \
        # .replace("o ' clock", "o'clock").replace("o 'clock", "o'clock") \
        # .replace("decades", "decade") \
        # .replace("tisíciletí", "milénium")
        # .replace("oclock", "o'clock")
        wordList = s.split()

        for idx, word in enumerate(wordList):
            #word = word.replace("'s", "")
            ##########
            # Czech Day Ordinals - we do not use 1st,2nd format
            #    instead we use full ordinal number names with specific format(suffix)
            #   Example: třicátého prvního > 31
            count_ordinals = 0
            if word == "prvního":
                count_ordinals = 1   # These two have different format
            elif word == "třetího":
                count_ordinals = 3
            elif word.endswith("ého"):
                tmp = word[:-3]
                tmp += ("ý")
                for nr, name in _ORDINAL_BASE_CS.items():
                    if name == tmp:
                        count_ordinals = nr

            # If number is bigger than 19 chceck if next word is also ordinal
            #  and count them together
            if count_ordinals > 19:
                if wordList[idx+1] == "prvního":
                    count_ordinals += 1   # These two have different format
                elif wordList[idx+1] == "třetího":
                    count_ordinals += 3
                elif wordList[idx+1].endswith("ého"):
                    tmp = wordList[idx+1][:-3]
                    tmp += ("ý")
                    for nr, name in _ORDINAL_BASE_CS.items():
                        if name == tmp and nr < 10:
                            # write only if sum makes acceptable count of days in month
                            if (count_ordinals + nr) <= 31:
                                count_ordinals += nr

            if count_ordinals > 0:
                word = str(count_ordinals)  # Write normalized valu into word
            if count_ordinals > 20:
                # If counted number is grather than 20, clear next word so it is not used again
                wordList[idx+1] = ""
            ##########
            # Remove inflection from czech months

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

    timeQualifiersAM = ['ráno', 'dopoledne']
    timeQualifiersPM = ['odpoledne', 'večer', 'noc', 'noci']
    timeQualifiersList = set(timeQualifiersAM + timeQualifiersPM)
    markers = ['na', 'v', 'do', 'na', 'tento',
               'okolo', 'toto', 'během', 'za', 'této']
    days = ['pondělí', 'úterý', 'středa',
            'čtvrtek', 'pátek', 'sobota', 'neděle']
    months = _MONTHS_CZECH
    recur_markers = days + [d + 'ho' for d in days] + \
        ['víkend', 'všední']  # Check this
    monthsShort = ['led', 'úno', 'bře', 'dub', 'kvě', 'čvn', 'čvc', 'srp',
                   'zář', 'říj', 'lis', 'pro']
    year_multiples = ["desetiletí", "století", "tisíciletí"]
    day_multiples = ["týden", "měsíc", "rok"]

    words = clean_string(text)

    for idx, word in enumerate(words):
        if word == "":
            continue

        word = _text_cs_inflection_normalize(word, 2)
        wordPrevPrev = _text_cs_inflection_normalize(
            words[idx - 2], 2) if idx > 1 else ""
        wordPrev = _text_cs_inflection_normalize(
            words[idx - 1], 2) if idx > 0 else ""
        wordNext = _text_cs_inflection_normalize(
            words[idx + 1], 2) if idx + 1 < len(words) else ""
        wordNextNext = _text_cs_inflection_normalize(
            words[idx + 2], 2) if idx + 2 < len(words) else ""

        # this isn't in clean string because I don't want to save back to words
        #word = word.rstrip('s')
        start = idx
        used = 0
        # save timequalifier for later
        # if word == "před" and dayOffset:
        #    dayOffset = - dayOffset
        #    used += 1
        if word == "nyní" and not datestr:
            resultStr = " ".join(words[idx + 1:])
            resultStr = ' '.join(resultStr.split())
            extractedDate = anchorDate.replace(microsecond=0)
            return [extractedDate, resultStr]
        elif wordNext in year_multiples:
            multiplier = None
            if is_numeric(word):
                multiplier = extract_number_cs(word)
            multiplier = multiplier or 1
            multiplier = int(multiplier)
            used += 2
            if wordNext == "desetiletí":
                yearOffset = multiplier * 10
            elif wordNext == "století":
                yearOffset = multiplier * 100
            elif wordNext == "tisíciletí":
                yearOffset = multiplier * 1000
        # couple of
        elif word == "2" and wordNext == "krát" and \
                wordNextNext in year_multiples:
            multiplier = 2
            used += 3
            if wordNextNext == "desetiletí":
                yearOffset = multiplier * 10
            elif wordNextNext == "století":
                yearOffset = multiplier * 100
            elif wordNextNext == "tisíciletí":
                yearOffset = multiplier * 1000
        elif word == "2" and wordNext == "krát" and \
                wordNextNext in day_multiples:
            multiplier = 2
            used += 3
            if wordNextNext == "rok":
                yearOffset = multiplier
            elif wordNextNext == "měsíc":
                monthOffset = multiplier
            elif wordNextNext == "týden":
                dayOffset = multiplier * 7
        elif word in timeQualifiersList:
            timeQualifier = word
        # parse today, tomorrow, day after tomorrow
        elif word == "dnes" and not fromFlag:
            dayOffset = 0
            used += 1
        elif word == "zítra" and not fromFlag:
            dayOffset = 1
            used += 1
        elif word == "den" and wordNext == "před" and wordNextNext == "včera" and not fromFlag:
            dayOffset = -2
            used += 3
        elif word == "před" and wordNext == "včera" and not fromFlag:
            dayOffset = -2
            used += 2
        elif word == "včera" and not fromFlag:
            dayOffset = -1
            used += 1
        elif (word == "den" and
              wordNext == "po" and
              wordNextNext == "zítra" and
              not fromFlag and
              (not wordPrev or not wordPrev[0].isdigit())):
            dayOffset = 2
            used = 3
            if wordPrev == "ten":
                start -= 1
                used += 1
                # parse 5 days, 10 weeks, last week, next week
        elif word == "den":
            if wordPrev and wordPrev[0].isdigit():
                dayOffset += int(wordPrev)
                start -= 1
                used = 2
                if wordPrevPrev == "před":
                    dayOffset = -dayOffset
                    used += 1
                    start -= 1

        elif word == "týden" and not fromFlag and wordPrev:
            if wordPrev[0].isdigit():
                dayOffset += int(wordPrev) * 7
                start -= 1
                used = 2
            elif wordPrev == "další" or wordPrev == "příští":
                dayOffset = 7
                start -= 1
                used = 2
            elif wordPrev == "poslední":
                dayOffset = -7
                start -= 1
                used = 2
                # parse 10 months, next month, last month
        elif word == "měsíc" and not fromFlag and wordPrev:
            if wordPrev[0].isdigit():
                monthOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "další" or wordPrev == "příští":
                monthOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "poslední":
                monthOffset = -1
                start -= 1
                used = 2
        # parse 5 years, next year, last year
        elif word == "rok" and not fromFlag and wordPrev:
            if wordPrev[0].isdigit():
                yearOffset = int(wordPrev)
                start -= 1
                used = 2
            elif wordPrev == "další" or wordPrev == "příští":
                yearOffset = 1
                start -= 1
                used = 2
            elif wordPrev == "poslední":
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
            if wordPrev == "další" or wordPrev == "příští":
                if dayOffset <= 2:
                    dayOffset += 7
                used += 1
                start -= 1
            elif wordPrev == "poslední":
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
            # Convert czech months to english
            datestr = _MONTHS_CONVERSION.get(m)
            if wordPrev and (wordPrev[0].isdigit() or
                             (wordPrev == " " and wordPrevPrev[0].isdigit())):
                if wordPrev == " " and wordPrevPrev[0].isdigit():
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

            # if no date indicators found, it may not be the month of May
            # may "i/we" ...
            # "... may be"
            # elif word == 'may' and wordNext in ['i', 'we', 'be']:
            #    datestr = ""

        # parse 5 days from tomorrow, 10 weeks from next thursday,
        # 2 months from July
        validFollowups = days + months + monthsShort
        validFollowups.append("dnes")
        validFollowups.append("zítra")
        validFollowups.append("včera")
        validFollowups.append("další")
        validFollowups.append("příští")
        validFollowups.append("poslední")
        validFollowups.append("teď")
        validFollowups.append("toto")
        validFollowups.append("této")
        validFollowups.append("tento")
        if (word == "od" or word == "po" or word == "do") and wordNext in validFollowups:
            used = 2
            fromFlag = True
            if wordNext == "zítra":
                dayOffset += 1
            elif wordNext == "včera":
                dayOffset -= 1
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
                if wordNext == "další" or wordPrev == "příští":
                    if dayOffset <= 2:
                        tmpOffset += 7
                    used += 1
                    start -= 1
                elif wordNext == "poslední":
                    tmpOffset -= 7
                    used += 1
                    start -= 1
                dayOffset += tmpOffset
        if used > 0:
            if start - 1 > 0 and (words[start - 1] == "toto" or words[start - 1] == "této" or words[start - 1] == "tento"):
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

        word = _text_cs_inflection_normalize(word, 2)
        wordPrevPrev = _text_cs_inflection_normalize(
            words[idx - 2], 2) if idx > 1 else ""
        wordPrev = _text_cs_inflection_normalize(
            words[idx - 1], 2) if idx > 0 else ""
        wordNext = _text_cs_inflection_normalize(
            words[idx + 1], 2) if idx + 1 < len(words) else ""
        wordNextNext = _text_cs_inflection_normalize(
            words[idx + 2], 2) if idx + 2 < len(words) else ""

        # parse noon, midnight, morning, afternoon, evening
        used = 0
        if word == "poledne":
            hrAbs = 12
            used += 1
        elif word == "půlnoc":
            hrAbs = 0
            used += 1
        elif word == "ráno":
            if hrAbs is None:
                hrAbs = 8
            used += 1
        elif word == "odpoledne":
            if hrAbs is None:
                hrAbs = 15
            used += 1
        elif word == "večer":
            if hrAbs is None:
                hrAbs = 19
            used += 1
            if (wordNext != "" and wordNext[0].isdigit() and ":" in wordNext):
                used -= 1
        elif word == "noci" or word == "noc":
            if hrAbs is None:
                hrAbs = 22
            #used += 1
            # if ((wordNext !='' and not wordNext[0].isdigit()) or wordNext =='') and \
            #    ((wordNextNext !='' and not wordNextNext[0].isdigit())or wordNextNext =='')  :
            #    used += 1
            # used += 1 ## NOTE this breaks other tests, TODO refactor me!

        # couple of time_unit
        elif word == "2" and wordNext == "krát" and \
                wordNextNext in ["hodin", "minut", "sekund"]:
            used += 3
            if wordNextNext == "hodin":
                hrOffset = 2
            elif wordNextNext == "minut":
                minOffset = 2
            elif wordNextNext == "sekund":
                secOffset = 2
        # parse half an hour, quarter hour
        elif word == "hodin" and \
                (wordPrev in markers or wordPrevPrev in markers):
            if wordPrev == "půl":
                minOffset = 30
            elif wordPrev == "čtvrt":
                minOffset = 15
            elif wordPrevPrev == "třičtvrtě":
                minOffset = 15
                if idx > 2 and words[idx - 3] in markers:
                    words[idx - 3] = ""
                words[idx - 2] = ""
            elif wordPrev == "během":
                hrOffset = 1
            else:
                hrOffset = 1
            if wordPrevPrev in markers:
                words[idx - 2] = ""
                if wordPrevPrev == "tato" or wordPrevPrev == "této":
                    daySpecified = True
            words[idx - 1] = ""
            used += 1
            hrAbs = -1
            minAbs = -1
            # parse 5:00 am, 12:00 p.m., etc
        # parse in a minute
        elif word == "minut" and wordPrev == "za":
            minOffset = 1
            words[idx - 1] = ""
            used += 1
        # parse in a second
        elif word == "sekund" and wordPrev == "za":
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
            if wordNext == "večer" or wordNext == "noci" or wordNextNext == "večer" \
                    or wordNextNext == "noci" or wordPrev == "večer" \
                    or wordPrev == "noci" or wordPrevPrev == "večer" \
                    or wordPrevPrev == "noci" or wordNextNextNext == "večer" \
                    or wordNextNextNext == "noci":
                remainder = "pm"
                used += 1
                if wordPrev == "večer" or wordPrev == "noci":
                    words[idx - 1] = ""
                if wordPrevPrev == "večer" or wordPrevPrev == "noci":
                    words[idx - 2] = ""
                if wordNextNext == "večer" or wordNextNext == "noci":
                    used += 1
                if wordNextNextNext == "večer" or wordNextNextNext == "noci":
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

                    # elif wordNext == "in" and wordNextNext == "the" and \
                    #        words[idx + 3] == "ráno":
                    #    remainder = "am"
                    #    used += 3
                    # elif wordNext == "in" and wordNextNext == "the" and \
                    #        words[idx + 3] == "odpoledne":
                    #    remainder = "pm"
                    #    used += 3
                    # elif wordNext == "in" and wordNextNext == "the" and \
                    #        words[idx + 3] == "večer":
                    #    remainder = "pm"
                    #    used += 3
                    elif wordNext == "ráno":
                        remainder = "am"
                        used += 2
                    elif wordNext == "odpoledne":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "večer":
                        remainder = "pm"
                        used += 2
                    elif wordNext == "toto" and wordNextNext == "ráno":
                        remainder = "am"
                        used = 2
                        daySpecified = True
                    elif wordNext == "na" and wordNextNext == "odpoledne":
                        remainder = "pm"
                        used = 2
                        daySpecified = True
                    elif wordNext == "na" and wordNextNext == "večer":
                        remainder = "pm"
                        used = 2
                        daySpecified = True
                    elif wordNext == "v" and wordNextNext == "noci":
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
                    if (int(strNum) > 100):  # and  #Check this
                        # (
                        #    wordPrev == "o" or
                        #    wordPrev == "oh"
                        # )):
                        # 0800 hours (pronounced oh-eight-hundred)
                        strHH = str(int(strNum) // 100)
                        strMM = str(int(strNum) % 100)
                        military = True
                        if wordNext == "hodin":
                            used += 1
                    elif (
                            (wordNext == "hodin" or
                             remainder == "hodin") and
                            word[0] != '0' and
                            # (wordPrev != "v" and wordPrev != "na")
                            wordPrev == "za"
                        and
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
                    elif wordNext == "minut" or \
                            remainder == "minut":
                        # "in 10 minutes"
                        minOffset = int(strNum)
                        used = 2
                        isTime = False
                        hrAbs = -1
                        minAbs = -1
                    elif wordNext == "sekund" \
                            or remainder == "sekund":
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
                        if wordNext == "hodin" or \
                                remainder == "hodin":
                            used += 1
                    elif wordNext and wordNext[0].isdigit():
                        # military time, e.g. "04 38 hours"
                        strHH = strNum
                        strMM = wordNext
                        military = True
                        used += 1
                        if (wordNextNext == "hodin" or
                                remainder == "hodin"):
                            used += 1
                    elif (
                            wordNext == "" or wordNext == "hodin" or
                            (
                                (wordNext == "v" or wordNext == "na") and
                                (
                                    wordNextNext == timeQualifier
                                )
                            ) or wordNext == 'večer' or
                            wordNextNext == 'večer'):

                        strHH = strNum
                        strMM = "00"
                        if wordNext == "hodin":
                            used += 1
                        if (wordNext == "v" or wordNext == "na"
                                or wordNextNext == "v" or wordNextNext == "na"):
                            used += (1 if (wordNext ==
                                           "v" or wordNext == "na") else 2)
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
                        elif remainder == "hodin":
                            remainder = ""

                    else:
                        isTime = False
            HH = int(strHH) if strHH else 0
            MM = int(strMM) if strMM else 0
            HH = HH + 12 if remainder == "pm" and HH < 12 else HH
            HH = HH - 12 if remainder == "am" and HH >= 12 else HH
            if (not military and
                    remainder not in ['am', 'pm', 'hodin', 'minut', 'sekund'] and
                    ((not daySpecified) or 0 <= dayOffset < 1)):

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

            # if wordPrev == "o" or wordPrev == "oh":
            #    words[words.index(wordPrev)] = ""

            if wordPrev == "brzy":
                hrOffset = -1
                words[idx - 1] = ""
                idx -= 1
            elif wordPrev == "pozdě":
                hrOffset = 1
                words[idx - 1] = ""
                idx -= 1
            if idx > 0 and wordPrev in markers:
                words[idx - 1] = ""
                if wordPrev == "toto" or wordPrev == "této":
                    daySpecified = True
            if idx > 1 and wordPrevPrev in markers:
                words[idx - 2] = ""
                if wordPrevPrev == "toto" or wordPrev == "této":
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

        extractedDate = extractedDate + relativedelta(hours=hrAbs,
                                                      minutes=minAbs)
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
        if words[idx] == "a" and \
                words[idx - 1] == "" and words[idx + 1] == "":
            words[idx] = ""

    resultStr = " ".join(words)
    resultStr = ' '.join(resultStr.split())
    return [extractedDate, resultStr]


def isFractional_cs(input_str, short_scale=True):
    """
    This function takes the given text and checks if it is a fraction.

    Args:
        input_str (str): the string to check if fractional
        short_scale (bool): use short scale if True, long scale if False
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    if input_str.endswith('iny', -3):  # leading number is bigger than one ( one třetina, two třetiny)
        # Normalize to format of one (třetiny > třetina)
        input_str = input_str[:len(input_str) - 1] + "a"

    fracts = {"celá": 1}  # first four numbers have little different format

    for num in _FRACTION_STRING_CS:  # Numbers from 2 to 1 hundret, more is not usualy used in common speech
        if num > 1:
            fracts[_FRACTION_STRING_CS[num]] = num

    if input_str.lower() in fracts:
        return 1.0 / fracts[input_str.lower()]
    return False


def extract_numbers_cs(text, short_scale=True, ordinals=False):
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
    results = _extract_numbers_with_text_cs(tokenize(text),
                                            short_scale, ordinals)
    return [float(result.value) for result in results]


class CzechNormalizer(Normalizer):
    with open(resolve_resource_file("text/cs-cz/normalize.json"), encoding='utf8') as f:
        _default_config = json.load(f)


def normalize_cs(text, remove_articles=True):
    """ Czech string normalization """
    return CzechNormalizer().normalize(text, remove_articles)


def _text_cs_inflection_normalize(word, arg):
    """
    Czech Inflection normalizer.

    This try to normalize known inflection. This function is called
    from multiple places, each one is defined with arg.

    Args:
        word [Word]
        arg [Int]

    Returns:
        word [Word]

    """
    if arg == 1:  # _extract_whole_number_with_text_cs
        # Number one (jedna)
        if len(word) == 5 and word.startswith("jed"):
            suffix = 'en', 'no', 'ny'
            if word.endswith(suffix, 3):
                word = "jedna"

        # Number two (dva)
        elif word == "dvě":
            word = "dva"

    elif arg == 2:  # extract_datetime_cs  TODO: This is ugly
        if word == "hodina":
            word = "hodin"
        if word == "hodiny":
            word = "hodin"
        if word == "hodinu":
            word = "hodin"
        if word == "minuta":
            word = "minut"
        if word == "minuty":
            word = "minut"
        if word == "minutu":
            word = "minut"
        if word == "minutu":
            word = "minut"
        if word == "sekunda":
            word = "sekund"
        if word == "sekundy":
            word = "sekund"
        if word == "sekundu":
            word = "sekund"
        if word == "dní":
            word = "den"
        if word == "dnů":
            word = "den"
        if word == "dny":
            word = "den"
        if word == "týdny":
            word = "týden"
        if word == "týdnů":
            word = "týden"
        if word == "měsíců":
            word = "měsíc"
        if word == "měsíce":
            word = "měsíc"
        if word == "měsíci":
            word = "měsíc"
        if word == "roky":
            word = "rok"
        if word == "roků":
            word = "rok"
        if word == "let":
            word = "rok"
        if word == "včerejšku":
            word = "včera"
        if word == "zítřku":
            word = "zítra"
        if word == "zítřejší":
            word = "zítra"
        if word == "ranní":
            word = "ráno"
        if word == "dopolední":
            word = "dopoledne"
        if word == "polední":
            word = "poledne"
        if word == "odpolední":
            word = "odpoledne"
        if word == "večerní":
            word = "večer"
        if word == "noční":
            word = "noc"
        if word == "víkendech":
            word = "víkend"
        if word == "víkendu":
            word = "víkend"
        if word == "všedních":
            word = "všední"
        if word == "všedním":
            word = "všední"

        # Months
        if word == "únoru":
            word = "únor"
        elif word == "červenci":
            word = "červenec"
        elif word == "července":
            word = "červenec"
        elif word == "listopadu":
            word = "listopad"
        elif word == "prosinci":
            word = "prosinec"

        elif word.endswith("nu") or word.endswith("na"):
            tmp = word[:-2]
            tmp += ("en")
            for name in _MONTHS_CZECH:
                if name == tmp:
                    word = name

    return word
