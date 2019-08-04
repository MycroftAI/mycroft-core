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
from collections import namedtuple
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from mycroft.util.lang.parse_common import is_numeric, look_for_fractions
from mycroft.util.lang.common_data_en import _ARTICLES, _NUM_STRING_EN, \
    _LONG_ORDINAL_STRING_EN, _LONG_SCALE_EN, \
    _SHORT_SCALE_EN, _SHORT_ORDINAL_STRING_EN

import re


def _invert_dict(original):
    """
    Produce a dictionary with the keys and values
    inverted, relative to the dict passed in.

    Args:
        original dict: The dict like object to invert

    Returns:
        dict

    """
    return {value: key for key, value in original.items()}


def _generate_plurals(originals):
    """
    Return a new set or dict containing the original values,
    all with 's' appended to them.

    Args:
        originals set(str) or dict(str, any): values to pluralize

    Returns:
        set(str) or dict(str, any)

    """
    if isinstance(originals, dict):
        return {key + 's': value for key, value in originals.items()}
    return {value + "s" for value in originals}


# negate next number (-2 = 0 - 2)
_NEGATIVES = {"negative", "minus"}

# sum the next number (twenty two = 20 + 2)
_SUMS = {'twenty', '20', 'thirty', '30', 'forty', '40', 'fifty', '50',
         'sixty', '60', 'seventy', '70', 'eighty', '80', 'ninety', '90'}

_MULTIPLIES_LONG_SCALE_EN = set(_LONG_SCALE_EN.values()) | \
                            _generate_plurals(_LONG_SCALE_EN.values())

_MULTIPLIES_SHORT_SCALE_EN = set(_SHORT_SCALE_EN.values()) | \
                             _generate_plurals(_SHORT_SCALE_EN.values())


# split sentence parse separately and sum ( 2 and a half = 2 + 0.5 )
_FRACTION_MARKER = {"and"}

# decimal marker ( 1 point 5 = 1 + 0.5)
_DECIMAL_MARKER = {"point", "dot"}

_STRING_NUM_EN = _invert_dict(_NUM_STRING_EN)
_STRING_NUM_EN.update(_generate_plurals(_STRING_NUM_EN))
_STRING_NUM_EN.update({
    "half": 0.5,
    "halves": 0.5,
    "couple": 2
})

_STRING_SHORT_ORDINAL_EN = _invert_dict(_SHORT_ORDINAL_STRING_EN)
_STRING_LONG_ORDINAL_EN = _invert_dict(_LONG_ORDINAL_STRING_EN)


# _Token is intended to be used in the number processing functions in
# this module. The parsing requires slicing and dividing of the original
# text. To ensure things parse correctly, we need to know where text came
# from in the original input, hence this nametuple.
_Token = namedtuple('_Token', 'word index')


class _ReplaceableNumber():
    """
    Similar to _Token, this class is used in number parsing.

    Once we've found a number in a string, this class contains all
    the info about the value, and where it came from in the original text.
    In other words, it is the text, and the number that can replace it in
    the string.
    """

    def __init__(self, value, tokens: [_Token]):
        self.value = value
        self.tokens = tokens

    def __bool__(self):
        return bool(self.value is not None and self.value is not False)

    @property
    def start_index(self):
        return self.tokens[0].index

    @property
    def end_index(self):
        return self.tokens[-1].index

    @property
    def text(self):
        return ' '.join([t.word for t in self.tokens])

    def __setattr__(self, key, value):
        try:
            getattr(self, key)
        except AttributeError:
            super().__setattr__(key, value)
        else:
            raise Exception("Immutable!")

    def __str__(self):
        return "({v}, {t})".format(v=self.value, t=self.tokens)

    def __repr__(self):
        return "{n}({v}, {t})".format(n=self.__class__.__name__, v=self.value,
                                      t=self.tokens)


def _tokenize(text):
    """
    Generate a list of token object, given a string.
    Args:
        text str: Text to tokenize.

    Returns:
        [_Token]

    """
    return [_Token(word, index) for index, word in enumerate(text.split())]


def _partition_list(items, split_on):
    """
    Partition a list of items.

    Works similarly to str.partition

    Args:
        items:
        split_on callable:
            Should return a boolean. Each item will be passed to
            this callable in succession, and partitions will be
            created any time it returns True.

    Returns:
        [[any]]

    """
    splits = []
    current_split = []
    for item in items:
        if split_on(item):
            splits.append(current_split)
            splits.append([item])
            current_split = []
        else:
            current_split.append(item)
    splits.append(current_split)
    return list(filter(lambda x: len(x) != 0, splits))


def _convert_words_to_numbers(text, short_scale=True, ordinals=False):
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
    tokens = _tokenize(text)
    numbers_to_replace = \
        _extract_numbers_with_text(tokens, short_scale, ordinals)
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


def _extract_numbers_with_text(tokens, short_scale=True,
                               ordinals=False, fractional_numbers=True):
    """
    Extract all numbers from a list of _Tokens, with the words that
    represent them.

    Args:
        [_Token]: The tokens to parse.
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
            _extract_number_with_text_en(tokens, short_scale,
                                         ordinals, fractional_numbers)

        if not to_replace:
            break

        results.append(to_replace)

        tokens = [
                    t if not
                    to_replace.start_index <= t.index <= to_replace.end_index
                    else
                    _Token(placeholder, t.index) for t in tokens
                  ]
    results.sort(key=lambda n: n.start_index)
    return results


def _extract_number_with_text_en(tokens, short_scale=True,
                                 ordinals=False, fractional_numbers=True):
    """
    This function extracts a number from a list of _Tokens.

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
        _extract_number_with_text_en_helper(tokens, short_scale,
                                            ordinals, fractional_numbers)
    while tokens and tokens[0].word in _ARTICLES:
        tokens.pop(0)
    return _ReplaceableNumber(number, tokens)


def _extract_number_with_text_en_helper(tokens,
                                        short_scale=True, ordinals=False,
                                        fractional_numbers=True):
    """
    Helper for _extract_number_with_text_en.

    This contains the real logic for parsing, but produces
    a result that needs a little cleaning (specific, it may
    contain leading articles that can be trimmed off).

    Args:
        tokens [_Token]:
        short_scale boolean:
        ordinals boolean:
        fractional_numbers boolean:

    Returns:
        int or float, [_Tokens]

    """
    if fractional_numbers:
        fraction, fraction_text = \
            _extract_fraction_with_text_en(tokens, short_scale, ordinals)
        if fraction:
            return fraction, fraction_text

        decimal, decimal_text = \
            _extract_decimal_with_text_en(tokens, short_scale, ordinals)
        if decimal:
            return decimal, decimal_text

    return _extract_whole_number_with_text_en(tokens, short_scale, ordinals)


def _extract_fraction_with_text_en(tokens, short_scale, ordinals):
    """
    Extract fraction numbers from a string.

    This function handles text such as '2 and 3/4'. Note that "one half" or
    similar will be parsed by the whole number function.

    Args:
        tokens [_Token]: words and their indexes in the original string.
        short_scale boolean:
        ordinals boolean:

    Returns:
        (int or float, [_Token])
        The value found, and the list of relevant tokens.
        (None, None) if no fraction value is found.

    """
    for c in _FRACTION_MARKER:
        partitions = _partition_list(tokens, lambda t: t.word == c)

        if len(partitions) == 3:
            numbers1 = \
                _extract_numbers_with_text(partitions[0], short_scale,
                                           ordinals, fractional_numbers=False)
            numbers2 = \
                _extract_numbers_with_text(partitions[2], short_scale,
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


def _extract_decimal_with_text_en(tokens, short_scale, ordinals):
    """
    Extract decimal numbers from a string.

    This function handles text such as '2 point 5'.

    Notes:
        While this is a helper for extractnumber_en, it also depends on
        extractnumber_en, to parse out the components of the decimal.

        This does not currently handle things like:
            number dot number number number

    Args:
        tokens [_Token]: The text to parse.
        short_scale boolean:
        ordinals boolean:

    Returns:
        (float, [_Token])
        The value found and relevant tokens.
        (None, None) if no decimal value is found.

    """
    for c in _DECIMAL_MARKER:
        partitions = _partition_list(tokens, lambda t: t.word == c)

        if len(partitions) == 3:
            numbers1 = \
                _extract_numbers_with_text(partitions[0], short_scale,
                                           ordinals, fractional_numbers=False)
            numbers2 = \
                _extract_numbers_with_text(partitions[2], short_scale,
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


def _extract_whole_number_with_text_en(tokens, short_scale, ordinals):
    """
    Handle numbers not handled by the decimal or fraction functions. This is
    generally whole numbers. Note that phrases such as "one half" will be
    handled by this function, while "one and a half" are handled by the
    fraction function.

    Args:
        tokens [_Token]:
        short_scale boolean:
        ordinals boolean:

    Returns:
        int or float, [_Tokens]
        The value parsed, and tokens that it corresponds to.

    """
    multiplies, string_num_ordinal, string_num_scale = \
        _initialize_number_data(short_scale)

    number_words = []  # type: [_Token]
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
        if word in _ARTICLES or word in _NEGATIVES:
            number_words.append(token)
            continue

        prev_word = tokens[idx - 1].word if idx > 0 else ""
        next_word = tokens[idx + 1].word if idx + 1 < len(tokens) else ""

        if word not in string_num_scale and \
                word not in _STRING_NUM_EN and \
                word not in _SUMS and \
                word not in multiplies and \
                not (ordinals and word in string_num_ordinal) and \
                not is_numeric(word) and \
                not isFractional_en(word, short_scale=short_scale) and \
                not look_for_fractions(word.split('/')):
            words_only = [token.word for token in number_words]
            if number_words and not all([w in _ARTICLES |
                                         _NEGATIVES for w in words_only]):
                break
            else:
                number_words = []
                continue
        elif word not in multiplies \
                and prev_word not in multiplies \
                and prev_word not in _SUMS \
                and not (ordinals and prev_word in string_num_ordinal) \
                and prev_word not in _NEGATIVES \
                and prev_word not in _ARTICLES:
            number_words = [token]
        elif prev_word in _SUMS and word in _SUMS:
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
        if word in _STRING_NUM_EN:
            val = _STRING_NUM_EN.get(word)
            current_val = val
        elif word in string_num_scale:
            val = string_num_scale.get(word)
            current_val = val
        elif ordinals and word in string_num_ordinal:
            val = string_num_ordinal[word]
            current_val = val

        # is the prev word an ordinal number and current word is one?
        # second one, third one
        if ordinals and prev_word in string_num_ordinal and val is 1:
            val = prev_val

        # is the prev word a number and should we sum it?
        # twenty two, fifty six
        if prev_word in _SUMS and val and val < 10:
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
            current_val = val

        # 2 fifths
        if not ordinals:
            next_val = isFractional_en(next_word, short_scale=short_scale)
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
            if prev_word in _SUMS and word not in _SUMS and current_val >= 10:
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
    multiplies = _MULTIPLIES_SHORT_SCALE_EN if short_scale \
        else _MULTIPLIES_LONG_SCALE_EN

    string_num_ordinal_en = _STRING_SHORT_ORDINAL_EN if short_scale \
        else _STRING_LONG_ORDINAL_EN

    string_num_scale_en = _SHORT_SCALE_EN if short_scale else _LONG_SCALE_EN
    string_num_scale_en = _invert_dict(string_num_scale_en)
    string_num_scale_en.update(_generate_plurals(string_num_scale_en))

    return multiplies, string_num_ordinal_en, string_num_scale_en


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
    return _extract_number_with_text_en(_tokenize(text),
                                        short_scale, ordinals).value




def extract_duration_ar(text):
    """
    Convert an arabic phrase (duration in spoken format) into a duration in a format of (number of seconds)
    i.e.ابدأ المؤقت لمدة سبعة وعشرين دقيقة 
    will be extracted as 27 minutes and then converted to 1620 seconds
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

    """Remove white spaces from the given text"""
    text = text.lstrip()
    """Split the text into array of words"""
    words = text.split()

    """Replace Haa and Alef letters to one format to easily deal with it i.e. ساعة to ساعه and أربع to اربع"""
    for i, word in enumerate(words):
        word = word.replace('ة','ه')
        word = word.replace('أ','ا')
        word = word.replace('إ','ا')
        word = word.replace('آ','ا')
        words[i] = word
    
    """Iterate over the array and extract the duration then parse it to seconds and return back the value"""
    for idx, word in enumerate(words):

        wordPrevPrev = words[idx - 2] if idx > 1 else ""

        wordPrev = words[idx - 1] if idx > 0 else ""

        # parse ساعه، ساعتين، اربع ساعات، نص - ربع ساعه
        if word == "ساعه":
            if wordPrev and (wordPrev == "نص" or wordPrev == "نصف"):
                time_units['minutes'] = 30
            elif wordPrev and wordPrev == "ربع":
                time_units['mintues'] = 15
            elif wordPrev and wordPrev != "ربع" and (wordPrev !="نص" or word != "نصف"):
                """the wordPrev might not be نص أو ربع it might be أربع، خمس ....so it needs to be sent to the normalize function to return its value in digit i.e. أربع to 4"""
                time_units['hours'] = int(normalize_ar(wordPrev))
            else:
                time_units['minutes'] = 60
        elif word == "ساعتين":
            time_units['minutes'] = 120
        elif word == "ساعات":
            if wordPrev:
                time_units['hours'] = int(normalize_ar(wordPrev))

        # parse دقيقه، دقيقتين، خمس دقايق
        elif word == "دقيقه":
            if wordPrev:
                if wordPrevPrev:
                    time_units['minutes'] = int(normalize_ar(wordPrevPrev+' '+wordPrev))
                else:
                    time_units['minutes'] = int(normalize_ar(wordPrev))
            else:
                time_units['minutes'] = 1 

        elif word == "دقيقتين":
                time_units['minutes'] = 2

        elif word == "دقايق" or word == "دقائق":
            if wordPrev:
                time_units['minutes'] = int(normalize_ar(wordPrev))

        # parse ثانيه، ثانيتين، اربع ثواني
        elif word == "ثانيه":
            if wordPrev:
                if wordPrevPrev:
                    time_units['seconds'] = int(normalize_ar(wordPrevPrev+' '+wordPrev))
                else:
                    time_units['seconds'] = int(normalize_ar(wordPrev))
            else:
                time_units['seconds'] = 1 

        elif word == "ثانيتين":
                time_units['seconds'] = 2

        elif word == "ثواني":
            if wordPrev:
                time_units['seconds'] = int(normalize_ar(wordPrev))

    """When the duration ectracted as number of hours or minutes or seconds, this function will be used to convert the duration to seconds"""
    duration = timedelta(**time_units) if any(time_units.values()) else None

    return (duration, text)


def extract_datetime_ar(string, dateNow, default_time):
    """ Convert a human date or datetime into an exact datetime

    Convert things like: اليوم - بكره - الأحد الجاي - الساعة أربعة العصر اليوم - سبعة الليل بتاريخ ثمانية أكتوبر

    into a datetime format 2019 10 08:07 00 00.  If a reference date is not provided, the current
    local date is used i.e. ذكرني أروح الساعة أربعه العصر it will set the date to today at 4:00 pm or if the time is passed then it will be tomorrow at 4:00. 

    Args:
        string (str): string containing datetime words
        dateNow (datetime): A reference date/time for "tommorrow", etc
        default_time (time): Time to set if no time was found in the string (we can use a defualt time also along with the default date)

    Returns:
        [datetime, str]: An array containing the datetime and the remaining
                         text not consumed in the parsing, or None if no
                         date or time related text was found.
    """


    """this function will be used after extracting the datetime from the given text, to check if we found a datetime, then we complete to parse it the datetime format, if not then return ZEROs"""
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


    
    """Initializing variables"""
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
    timeQualifiersAM = ['فجرا','صباحا','الصباح','الفجر','الصبح']
    timeQualifiersPM = ['الظهر', 'العصر', 'المغرب','الليل','ظهرا','عصرا','ليلا']
    timeQualifiersList = set(timeQualifiersAM + timeQualifiersPM)
    days = ['الاحد', 'الاثنين', 'الثلاثاء','الاربعاء', 'الخميس', 'الجمعه','السبت']
    ArabicMonths = ['جانيوري', 'فبراير', 'مارس', 'ابريل', 'ماي', 'جون','جولاي', 'اوقست', 'سبتمبر', 'اكتوبر', 'نوفمبر','ديسمبر']
    months = ['january', 'february', 'march', 'april', 'may', 'june','july', 'august', 'september', 'october',  'november','december']
    todayWords = ['اليوم','الليله']
    tomorrowWords = ['غدا','بكره']
    


    """Remove white spaces from the given text"""
    string = string.lstrip()
    """Split the text into array of words"""
    words = string.split()
    
    """Replace Haa and Alef letters to one format to easily deal with it i.e. ساعة to ساعه and أربع to اربع"""
    for i, word in enumerate(words):
        word = word.replace('ة','ه')
        word = word.replace('أ','ا')
        word = word.replace('إ','ا')
        word = word.replace('آ','ا')
        words[i] = word
        
        
    """Iterate through the array and extract the date from the given text (we did not parse it yet, just extract it and save its value in the variables; consider it as a preparation phase before 
    the real parsing"""
    # parse date
    for idx, word in enumerate(words):
        if word == "":
            continue
        wordPrevPrev = words[idx - 2] if idx > 1 else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""

        start = idx
        used = 0


        # parse اليوم، بكره
        """If the word is today, then the dayOffset is Zero, it means to need to increment the date"""
        if word in todayWords and not fromFlag:
            dayOffset = 0
            used += 1
        elif word in tomorrowWords and not fromFlag:
            dayOffset = 1
            used += 1
              
        # parse الأحد، الاثنين،... الجمعة
        #If the day is a weekday, then get its index from the array of the days and subtract it from today i.e. if the day is today then 0-0=0 it will be today, if tomorrow then, 1-0=0
        elif word in days and not fromFlag:
            d = days.index(word)
            dayOffset = (d) - int(today)
            used = 1
            """if for example today is tuesday ( index 2) and the day is next sunday (index 0), then the dayOffset is 0-2 = -2 (to solve that we add 7 to it)"""
            if dayOffset <= 0:
                dayOffset += 7

         # parse ثمانية أكتوبر
        #if the word is a month i.e. اكتوبر then we rteieve its index from the array, then we get the English word from from the other array (because the parsin function can only work with the 
        #English monoths
        elif word in ArabicMonths and not fromFlag:

            m = ArabicMonths.index(word)
            datestr = months[m]
            if wordPrev:
                """if there is a number before the month, then get its digit format from the normalize function and concatenating them together"""
                number=normalize_ar(wordPrev)
                datestr += " "+ number
                used += 1
                start -= 1

     
    """Iterate through the array and extract the time from the given text (we did not parse it yet, just extract it and save its value in the variables; consider it as a preparation phase before 
    the real parsing"""
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
        
        # parse الظهر، الصباح، العصر، الليل
        used = 0
        
        if word in timeQualifiersAM:
            """if we say ذكرني اروح الساعه سبعه الصباح it will convert the previous word of الصباح to 7"""
            if wordPrev and not ':' in wordPrev:
                hrAbs = int(normalize_ar(wordPrev))
                used += 1
            #if we say ذكرني اروح على الصباح it will convert the previous word of الصباح to 8 the defualt value, becaue the user did not specify exact time
            elif word == "الصباح" or word == "صباحا" or word == "الصبح":
                if hrAbs is None:
                    hrAbs = 8
                used += 1
        elif word in timeQualifiersPM:
            """if we say ذكرني اروح الساعه سبعه الليل it will convert the previous word of الليل to 7+12 = 19"""
            if wordPrev and not ':' in wordPrev:
                hrAbs = int(normalize_ar(wordPrev))+12
                used += 1
            #if we say ذكرني اروح على الظهر - العصر it will convert the previous word of الظهر to 12 the defualt value, becaue the user did not specify exact time
            elif word == "الظهر" or word == "ظهرا":
                hrAbs = 12
                used += 1
            elif word == "العصر" or word == "عصرا":
                if hrAbs is None:
                    hrAbs = 16
                used += 1
            elif word == "الليل" or word == "ليلا":
                if hrAbs is None:
                    hrAbs = 20
                used += 1

       
        # parse نص ساعة، ربع ساعة
        if word == "ساعه":
            """if it iterate over the array and find the word ساعه then it will see its previous word, if it is نص the minutesOffset will be 30 and so on"""
            if wordPrev and (wordPrev == "نص" or wordPrev =="نصف"):
                minOffset = 30
            elif wordPrev and wordPrev == "ربع":
                minOffset = 15
            else:
                minOffset = 60

        # parse دقيقة، دقيقتين، أربع دقايق
        elif word == "دقيقه":
            """if it iterate over the array and find the word دقيقه then it will see its previous word i.e. ثلاث the minutesOffset will be given the normalized format of it (digit)"""
            if wordPrev:
                if wordPrevPrev:
                    minOffset = int(normalize_ar(wordPrevPrev+' '+wordPrev))
                else:
                    minOffset = int(normalize_ar(wordPrev))
            else:
                minOffset = 1 

        elif word == "دقيقتين":
                minOffset = 2

        elif word == "دقايق" or word =="دقائق":
            if wordPrev:
                minOffset = int(normalize_ar(wordPrev))

        # parse ثانية، ثانيتين، خمس ثواني
        elif word == "ثانيه":
            if wordPrev:
                if wordPrevPrev:
                    secOffset = int(normalize_ar(wordPrevPrev+' '+wordPrev))
                else:
                    secOffset = int(normalize_ar(wordPrev))
            else:
                secOffset = 1 

        elif word == "ثانيتين":
                secOffset = 2

        elif word == "ثواني":
            if wordPrev:
                secOffset = int(normalize_ar(wordPrev))

  
      
    """after extracting the date and time and preparing them and storing into the variable, now the real parsing will start here"""
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
        for num in _SHORT_ORDINAL_STRING_EN:
            if num > 2:
                fracts[_SHORT_ORDINAL_STRING_EN[num]] = num
    else:
        for num in _LONG_ORDINAL_STRING_EN:
            if num > 2:
                fracts[_LONG_ORDINAL_STRING_EN[num]] = num

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
    results = _extract_numbers_with_text(_tokenize(text),
                                         short_scale, ordinals)
    return [float(result.value) for result in results]



def normalize_ar(text):
    """ Arabic string normalization, convert the spoken number to digit format, i.e. سبعة وعشرين to 27"""

    """numers in الفصحى"""
    Standard1 = ["صفر", "الواحده", "الثانيه", "الثالثه", "الرابعه", "الخامسه", "السادسه", "السابعه", "الثامنه", "التاسعه", "العاشره", "الحاديه عشر", "الثانيه عشر", "ثلاثه عشر", "اربعه عشر", "خمسه عشر", "سته عشر",
                       "سبعه عشر", "ثمانيه عشر", "تسعه عشر", "عشرون","واحد وعشرون","اثنان وعشرون","ثلاثه وعشرون","اربعه وعشرون","خمسه وعشرون","سته وعشرون","سبعه وعشرون","ثمانيه وعشرون","تسعه وعشرون","ثلاثين","واحد وثلاثون","اثنان وثلاثون","ثلاثه وثلاثون","اربعه وثلاثون","خمسه وثلاثون","سته وثلاثون","سبعه وثلاثون","ثمانيه وثلاثون","تسعه وثلاثون","اربعون","واحد واربعون","اثنان واربعون","ثلاثه واربعون","اربعه واربعون","خمسه واربعون","سته واربعون","سبعه واربعون","ثمانيه واربعون","تسعه واربعون","خمسون","واحد وخمسون","اثنان وخمسون","ثلاثه وخمسون","اربعه وخمسون","خمسه وخمسون","سته وخمسون","سبعه وخمسون","ثمانيه وخمسون","تسعه وخمسون","ستون"]
   
    Standard2 = ["احد عشر","اثنا عشر"]

    """numers in العامية"""
    Dialect = ["صفر", "وحده", "ثنتين", "ثلاثه", "اربعه", "خمسه", "سته", "سبعه", "ثمانيه", "تسعه", "عشره", "احدعش", "اثنعش", "ثلاث طعش", "اربع طعش", "خمس طعش", "ست طعش",
                       "سبع طش", "ثمان طعش", "تسع طعش", "عشرين","واحد وعشرين","اثنين وعشرين","ثلاثه وعشرين","اربعه وعشرين","خمسه وعشرين","سته وعشرين","سبعه وعشرين","ثمانيه وعشرين","تسعه وعشرين","ثلاثين","واحد وثلاثين","اثنين وثلاثين","ثلاثه وثلاثين","اربعه وثلاثين","خمسه وثلاثين","سته وثلاثين","سبعه وثلاثين","ثمانيه وثلاثين","تسعه وثلاثين","اربعين","واحد واربعين","اثنين واربعين","ثلاثه واربعين","اربعه واربعين","خمسه واربعين","سته واربعين","سبعه واربعين","ثمانيه واربعين","تسعه واربعين","خمسين","واحد وخمسين","اثنين وخمسين","ثلاثه وخمسين","اربعه وخمسين","خمسه وخمسين","سته وخمسين","سبعه وخمسين","ثمانيه وخمسين","تسعه وخمسين","ستين"]
    """some numbers can say by the user without Haa letter"""
    NormalizedDialect = ["صفر", "واحد", "اثنين", "ثلاث", "اربع", "خمس", "ست", "سبع", "ثمان", "تسع", "عشر"]

    

    """the given text (number) will be searched over these arrays, if the number is found, then the index of it will be return (which represent the number in digit"""
    if text in Standard1:
        word = str(Standard1.index(text))
    elif text in Standard2:
        word = str(Standard1.index(text)+10)
    elif text in Dialect:
        word = str(Dialect.index(text))
    elif text in NormalizedDialect:
        word = str(NormalizedDialect.index(text))
    else:
        word = text


    

    return word  # strip the initial space
