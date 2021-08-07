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

from .format_common import convert_to_mixed_fraction
from lingua_franca.lang.common_data_nl import _NUM_POWERS_OF_TEN, \
    _NUM_STRING_NL, _FRACTION_STRING_NL, _EXTRA_SPACE_NL, _MONTHS_NL
from math import floor


def nice_number_nl(number, speech=True, denominators=range(1, 21)):
    """ Dutch helper for nice_number
    This function formats a float to human understandable functions. Like
    4.5 becomes "4 einhalb" for speech and "4 1/2" for text
    Args:
        number (int or float): the float to format
        speech (bool): format for speech (True) or display (False)
        denominators (iter of ints): denominators to use, default [1 .. 20]
    Returns:
        (str): The formatted string.
    """
    result = convert_to_mixed_fraction(number, denominators)
    if not result:
        # Give up, just represent as a 3 decimal number
        return str(round(number, 3)).replace(".", ",")
    whole, num, den = result
    if not speech:
        if num == 0:
            # TODO: Number grouping?  E.g. "1,000,000"
            return str(whole)
        else:
            return '{} {}/{}'.format(whole, num, den)
    if num == 0:
        return str(whole)
    den_str = _FRACTION_STRING_NL[den]
    if whole == 0:
        if num == 1:
            return_string = 'één {}'.format(den_str)
        else:
            return_string = '{} {}'.format(num, den_str)
    elif num == 1:
        return_string = '{} en één {}'.format(whole, den_str)
    else:
        return_string = '{} en {} {}'.format(whole, num, den_str)

    return return_string


def pronounce_number_nl(number, places=2, short_scale=True, scientific=False,
                        ordinals=False):
    """
    Convert a number to it's spoken equivalent

    For example, '5.2' would return 'five point two'

    Args:
        number(float or int): the number to pronounce (under 100)
        places(int): maximum decimal places to speak
        short_scale (bool) : use short (True) or long scale (False)
            https://en.wikipedia.org/wiki/Names_of_large_numbers
        scientific (bool): pronounce in scientific notation
        ordinals (bool): pronounce in ordinal form "first" instead of "one"
    Returns:
        (str): The pronounced number
    """
    # TODO short_scale, scientific and ordinals
    # currently ignored

    def pronounce_triplet_nl(num):
        result = ""
        num = floor(num)
        if num > 99:
            hundreds = floor(num / 100)
            if hundreds > 0:
                result += _NUM_STRING_NL[
                    hundreds] + _EXTRA_SPACE_NL + 'honderd' + _EXTRA_SPACE_NL
                num -= hundreds * 100
        if num == 0:
            result += ''  # do nothing
        elif num <= 20:
            result += _NUM_STRING_NL[num]  # + _EXTRA_SPACE_DA
        elif num > 20:
            ones = num % 10
            tens = num - ones
            if ones > 0:
                result += _NUM_STRING_NL[ones] + _EXTRA_SPACE_NL
                if tens > 0:
                    result += 'en' + _EXTRA_SPACE_NL
            if tens > 0:
                result += _NUM_STRING_NL[tens] + _EXTRA_SPACE_NL
        return result

    def pronounce_fractional_nl(num,
                                places):  # fixed number of places even with
        # trailing zeros
        result = ""
        place = 10
        while places > 0:  # doesn't work with 1.0001 and places = 2: int(
            # number*place) % 10 > 0 and places > 0:
            result += " " + _NUM_STRING_NL[int(num * place) % 10]
            if int(num * place) % 10 == 1:
                result += ''  # "1" is pronounced "eins" after the decimal
                # point
            place *= 10
            places -= 1
        return result

    def pronounce_whole_number_nl(num, scale_level=0):
        if num == 0:
            return ''

        num = floor(num)
        result = ''
        last_triplet = num % 1000

        if last_triplet == 1:
            if scale_level == 0:
                if result != '':
                    result += '' + 'één'
                else:
                    result += "één"
            elif scale_level == 1:
                result += 'één' + _EXTRA_SPACE_NL + 'duizend' + _EXTRA_SPACE_NL
            else:
                result += "één " + _NUM_POWERS_OF_TEN[scale_level] + ' '
        elif last_triplet > 1:
            result += pronounce_triplet_nl(last_triplet)
            if scale_level == 1:
                # result += _EXTRA_SPACE_DA
                result += 'duizend' + _EXTRA_SPACE_NL
            if scale_level >= 2:
                # if _EXTRA_SPACE_DA == '':
                #    result += " "
                result += " " + _NUM_POWERS_OF_TEN[scale_level] + ' '
            if scale_level >= 2:
                if scale_level % 2 == 0:
                    result += ""  # Miljioen
                result += ""  # Miljard, Miljoen

        num = floor(num / 1000)
        scale_level += 1
        return pronounce_whole_number_nl(num,
                                         scale_level) + result + ''

    result = ""
    if abs(number) >= 1000000000000000000000000:  # cannot do more than this
        return str(number)
    elif number == 0:
        return str(_NUM_STRING_NL[0])
    elif number < 0:
        return "min " + pronounce_number_nl(abs(number), places)
    else:
        if number == int(number):
            return pronounce_whole_number_nl(number)
        else:
            whole_number_part = floor(number)
            fractional_part = number - whole_number_part
            result += pronounce_whole_number_nl(whole_number_part)
            if places > 0:
                result += " komma"
                result += pronounce_fractional_nl(fractional_part, places)
            return result


def pronounce_ordinal_nl(number):
    """
    This function pronounces a number as an ordinal

    1 -> first
    2 -> second

    Args:
        number (int): the number to format
    Returns:
        (str): The pronounced number string.
    """
    ordinals = ["nulste", "eerste", "tweede", "derde", "vierde", "vijfde",
                "zesde", "zevende", "achtste"]
    # only for whole positive numbers including zero
    if number < 0 or number != int(number):
        return number
    if number < 4:
        return ordinals[number]
    if number < 8:
        return pronounce_number_nl(number) + "de"
    if number < 9:
        return pronounce_number_nl(number) + "ste"
    if number < 20:
        return pronounce_number_nl(number) + "de"
    return pronounce_number_nl(number) + "ste"


def nice_time_nl(dt, speech=True, use_24hour=False, use_ampm=False):
    """
    Format a time to a comfortable human format

    For example, generate 'five thirty' for speech or '5:30' for
    text display.

    Args:
        dt (datetime): date to format (assumes already in local timezone)
        speech (bool): format for speech (default/True) or display (False)=Fal
        use_24hour (bool): output in 24-hour/military or 12-hour format
        use_ampm (bool): include the am/pm for 12-hour format
    Returns:
        (str): The formatted time string
    """
    if use_24hour:
        # e.g. "03:01" or "14:22"
        string = dt.strftime("%H:%M")
    else:
        if use_ampm:
            # e.g. "3:01 AM" or "2:22 PM"
            string = dt.strftime("%I:%M %p")
        else:
            # e.g. "3:01" or "2:22"
            string = dt.strftime("%I:%M")
        if string[0] == '0':
            string = string[1:]  # strip leading zeros

    if not speech:
        return string

    # Generate a speakable version of the time
    speak = ""
    if use_24hour:
        speak += pronounce_number_nl(dt.hour)
        speak += " uur"
        if not dt.minute == 0:  # zero minutes are not pronounced, 13:00 is
            # "13 uur" not "13 hundred hours"
            speak += " " + pronounce_number_nl(dt.minute)
        return speak  # ampm is ignored when use_24hour is true
    else:
        if dt.hour == 0 and dt.minute == 0:
            return "Middernacht"
        hour = dt.hour % 12
        if dt.minute == 0:
            hour = _fix_hour_nl(hour)
            speak += pronounce_number_nl(hour)
            speak += " uur"
        elif dt.minute == 30:
            speak += "half "
            hour += 1
            hour = _fix_hour_nl(hour)
            speak += pronounce_number_nl(hour)
        elif dt.minute == 15:
            speak += "kwart over "
            hour = _fix_hour_nl(hour)
            speak += pronounce_number_nl(hour)
        elif dt.minute == 45:
            speak += "kwart voor "
            hour += 1
            hour = _fix_hour_nl(hour)
            speak += pronounce_number_nl(hour)
        elif dt.minute > 30:
            speak += pronounce_number_nl(60 - dt.minute)
            speak += " voor "
            hour += 1
            hour = _fix_hour_nl(hour)
            speak += pronounce_number_nl(hour)
        else:
            speak += pronounce_number_nl(dt.minute)
            speak += " over "
            hour = _fix_hour_nl(hour)
            speak += pronounce_number_nl(hour)

        if use_ampm:
            speak += nice_part_of_day_nl(dt)

        return speak


def _fix_hour_nl(hour):
    hour = hour % 12
    if hour == 0:
        hour = 12
    return hour


def nice_part_of_day_nl(dt, speech=True):
    if dt.hour < 6:
        return " 's nachts"
    if dt.hour < 12:
        return " 's ochtends"
    if dt.hour < 18:
        return " 's middags"
    if dt.hour < 24:
        return " 's avonds"
    raise ValueError('dt.hour is bigger than 24')


def nice_response_nl(text):
    # check for months and call _nice_ordinal_nl declension of ordinals
    # replace "^" with "tot de macht" (to the power of)
    words = text.split()

    for idx, word in enumerate(words):
        if word.lower() in _MONTHS_NL:
            text = _nice_ordinal_nl(text)

        if word == '^':
            wordNext = words[idx + 1] if idx + 1 < len(words) else ""
            if wordNext.isnumeric():
                words[idx] = "tot de macht"
                text = " ".join(words)
    return text


def _nice_ordinal_nl(text, speech=True):
    # check for months for declension of ordinals before months
    # depending on articles/prepositions
    normalized_text = text
    words = text.split()
    for idx, word in enumerate(words):
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        if word[:-1].isdecimal():
            if wordNext.lower() in _MONTHS_NL:
                if wordPrev == 'de':
                    word = pronounce_ordinal_nl(int(word))
                else:
                    word = pronounce_number_nl(int(word))
                words[idx] = word
    normalized_text = " ".join(words)
    return normalized_text
