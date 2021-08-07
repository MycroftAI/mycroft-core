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
from lingua_franca.lang.common_data_fa import _FARSI_BIG, \
    _FARSI_ONES, _FARSI_TENS, _FARSI_HUNDREDS, _FORMAL_VARIANT

import re
import json
from lingua_franca.internal import resolve_resource_file


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def _parse_sentence(text):
    for key, value in _FORMAL_VARIANT.items():
        text = text.replace(key, value)
    ar = text.split()
    result = []
    current_number = 0
    current_words = []
    s = 0
    step = 10
    mode = 'init'
    def finish_num():
        nonlocal current_number
        nonlocal s
        nonlocal result
        nonlocal mode
        nonlocal current_words
        current_number += s
        if current_number != 0:
            result.append((current_number, current_words))
        s = 0
        current_number = 0
        current_words = []
        mode = 'init'
    for x in ar:
        if x == "و":
            if mode == 'num_ten' or mode == 'num_hundred' or mode == 'num_one':
                mode += '_va'
                current_words.append(x)
            elif mode == 'num':
                current_words.append(x)    
            else:
                finish_num()
                result.append(x)
        elif x == "نیم":
            current_words.append(x)
            current_number += 0.5
            finish_num()
        elif x in _FARSI_ONES:
            t = _FARSI_ONES.index(x)
            if mode != 'init' and mode != 'num_hundred_va' and mode != 'num':
                if not(t < 10 and mode == 'num_ten_va'):
                    finish_num()
            current_words.append(x)
            s += t
            mode = 'num_one'
        elif x in _FARSI_TENS:
            if mode != 'init' and mode != 'num_hundred_va' and mode != 'num':
                finish_num()
            current_words.append(x)
            s += _FARSI_TENS.index(x)*10
            mode = 'num_ten'
        elif x in _FARSI_HUNDREDS:
            if mode != 'init' and mode != 'num':
                finish_num()
            current_words.append(x)
            s += _FARSI_HUNDREDS.index(x)*100
            mode = 'num_hundred'
        elif x in _FARSI_BIG:
            current_words.append(x)
            d = _FARSI_BIG.index(x)
            if mode == 'init' and d == 1:
                s = 1
            s *= 10**(3*d)
            current_number += s
            s = 0
            mode = 'num'
        elif _is_number(x):
            current_words.append(x)
            current_number = float(x)
            finish_num()
        else:
            finish_num()
            result.append(x)
    if mode[:3] == 'num':
        finish_num()
    return result


_time_units = {
    'ثانیه': timedelta(seconds=1),
    'دقیقه': timedelta(minutes=1),
    'ساعت': timedelta(hours=1),
}

_date_units = {
    'روز': timedelta(days=1),
    'هفته': timedelta(weeks=1),
}

def extract_duration_fa(text):
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
    remainder = []
    ar = _parse_sentence(text)
    current_number = None
    result = timedelta(0)
    for x in ar:
        if x == "و":
            continue
        elif type(x) == tuple:
            current_number = x
        elif x in _time_units:
            result += _time_units[x] * current_number[0]
            current_number = None
        elif x in _date_units:
            result += _date_units[x] * current_number[0]
            current_number = None
        else:
            if current_number:
                remainder.extend(current_number[1])
            remainder.append(x)
            current_number = None
    return (result, " ".join(remainder))


def extract_datetime_fa(text, anchorDate=None, default_time=None):
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
    if text == "":
        return None
    text = text.lower().replace('‌', ' ').replace('.', '').replace('،', '') \
        .replace('?', '').replace("پس فردا", "پسفردا") \
        .replace('یک شنبه', 'یکشنبه') \
        .replace('دو شنبه', 'دوشنبه') \
        .replace('سه شنبه', 'سهشنبه') \
        .replace('چهار شنبه', 'چهارشنبه') \
        .replace('پنج شنبه', 'پنجشنبه') \
        .replace('بعد از ظهر', 'بعدازظهر') \
        
        
    if not anchorDate:
        anchorDate = datetime.now()
    today = anchorDate.replace(hour=0, minute=0, second=0, microsecond=0)
    today_weekday = int(anchorDate.strftime("%w"))
    weekday_names = [
        'دوشنبه',
        'سهشنبه',
        'چهارشنبه',
        'پنجشنبه',
        'جمعه',
        'شنبه',
        'یکشنبه',
    ]
    daysDict = {
        'پریروز': today + timedelta(days= -2),
        'دیروز': today + timedelta(days= -1),
        'امروز': today,
        'فردا': today + timedelta(days= 1),
        'پسفردا': today + timedelta(days= 2),
    }
    timesDict = {
        'صبح': timedelta(hours=8),
        'بعدازظهر': timedelta(hours=15),
    }
    exactDict = {
        'الان': anchorDate,
    }
    nextWords = ["بعد", "دیگه"]
    prevWords = ["پیش", "قبل"]
    ar = _parse_sentence(text)
    mode = 'none'
    number_seen = None
    delta_seen = timedelta(0)
    remainder = []
    result = None
    for x in ar:
        handled = 1
        if mode == 'finished':
            remainder.append(x)
        elif x == 'و' and mode[:5] == 'delta':
            pass
        elif type(x) == tuple:
            number_seen = x
        elif x in weekday_names:
            dayOffset = (weekday_names.index(x) + 1) - today_weekday
            if dayOffset < 0:
                dayOffset += 7
            result = today + timedelta(days=dayOffset)
            mode = 'time'
        elif x in exactDict:
            result = exactDict[x]
            mode = 'finished'
        elif x in daysDict:
            result = daysDict[x]
            mode = 'time'
        elif x in timesDict and mode == 'time':
            result += timesDict[x]
            mode = 'finish'
        elif x in _date_units:
            k = 1
            if (number_seen):
                k = number_seen[0]
                number_seen = None
            delta_seen += _date_units[x] * k
            if mode != 'delta_time':
                mode = 'delta_date'
        elif x in _time_units:
            k = 1
            if (number_seen):
                k = number_seen[0]
                number_seen = None
            delta_seen += _time_units[x] * k
            mode = 'delta_time'
        elif x in nextWords or x in prevWords:
            # Give up instead of incorrect result
            if mode == 'time':
                return None
            sign = 1 if x in nextWords else -1
            if mode == 'delta_date':
                result = today + delta_seen
                mode = 'time'
            elif mode == 'delta_time':
                result = anchorDate + delta_seen
                mode = 'finished'
            else:
                handled = 0
        else:
            handled = 0
        if handled == 1:
            continue
        if number_seen:
            remainder.extend(number_seen[1])
            number_seen = None
        remainder.append(x)
    return (result, " ".join(remainder))

def is_fractional_fa(input_str, short_scale=True):
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
        for num in _SHORT_ORDINAL_FA:
            if num > 2:
                fracts[_SHORT_ORDINAL_FA[num]] = num
    else:
        for num in _LONG_ORDINAL_FA:
            if num > 2:
                fracts[_LONG_ORDINAL_FA[num]] = num

    if input_str.lower() in fracts:
        return 1.0 / fracts[input_str.lower()]
    return False


def extract_numbers_fa(text, short_scale=True, ordinals=False):
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

    ar = _parse_sentence(text)
    result = []
    for x in ar:
        if type(x) == tuple:
            result.append(x[0])
    return result


def extract_number_fa(text, ordinals=False):
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
    x = extract_numbers_fa(text, ordinals=ordinals)
    if (len(x) == 0):
        return False
    return x[0]

class EnglishNormalizer(Normalizer):
    with open(resolve_resource_file("text/en-us/normalize.json")) as f:
        _default_config = json.load(f)


def normalize_fa(text, remove_articles=True):
    """ English string normalization """
    return EnglishNormalizer().normalize(text, remove_articles)
