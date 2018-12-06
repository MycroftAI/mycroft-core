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

from mycroft.util.lang.format_common import convert_to_mixed_fraction
from math import floor

months = ['január', 'február', 'március', 'április', 'május', 'június',
          'július', 'augusztus', 'szeptember', 'október', 'november',
          'december']

NUM_STRING_HU = {
    0: 'nulla',
    1: 'egy',
    2: 'kettő',
    3: 'három',
    4: 'négy',
    5: 'öt',
    6: 'hat',
    7: 'hét',
    8: 'nyolc',
    9: 'kilenc',
    10: 'tíz',
    11: 'tizenegy',
    12: 'tizenkettő',
    13: 'tizenhárom',
    14: 'tizennégy',
    15: 'tizenöt',
    16: 'tizenhat',
    17: 'tizenhét',
    18: 'tizennyolc',
    19: 'tizenkilenc',
    20: 'húsz',
    30: 'harminc',
    40: 'negyven',
    50: 'ötven',
    60: 'hatvan',
    70: 'hetven',
    80: 'nyolcvan',
    90: 'kilencven',
    100: 'száz'
}

# Hungarian uses "long scale"
#    https://en.wikipedia.org/wiki/Long_and_short_scales
# Currently, numbers are limited to 1000000000000000000000000,
# but NUM_POWERS_OF_TEN can be extended to include additional number words

NUM_POWERS_OF_TEN = [
    '', 'ezer', 'millió', 'milliárd', 'billió', 'billiárd', 'trillió',
    'trilliárd'
]

FRACTION_STRING_HU = {
    2: 'fél',
    3: 'harmad',
    4: 'negyed',
    5: 'ötöd',
    6: 'hatod',
    7: 'heted',
    8: 'nyolcad',
    9: 'kilenced',
    10: 'tized',
    11: 'tizenegyed',
    12: 'tizenketted',
    13: 'tizenharmad',
    14: 'tizennegyed',
    15: 'tizenötöd',
    16: 'tizenhatod',
    17: 'tizenheted',
    18: 'tizennyolcad',
    19: 'tizenkilenced',
    20: 'huszad'
}

# Numbers below 2 thousand are written in one word in Hungarian
# Numbers above 2 thousand are separated by hyphens
# In some circumstances it may better to seperate individual words
# Set EXTRA_SPACE=" " for separating numbers below 2 thousand (
# orthographically incorrect)
# Set EXTRA_SPACE="" for correct spelling, this is standard

# EXTRA_SPACE = " "
EXTRA_SPACE = ""


def _get_vocal_type(word):
    # checks the vocal attributes of a word
    vowels_high = len([char for char in word if char in 'eéiíöőüű'])
    vowels_low = len([char for char in word if char in 'aáoóuú'])
    if vowels_high != 0 and vowels_low != 0:
        return 2                                   # 2: type is mixed
    return 0 if vowels_high == 0 else 1            # 0: type is low, 1: is high


def nice_number_hu(number, speech, denominators):
    """ Hungarian helper for nice_number

    This function formats a float to human understandable functions. Like
    4.5 becomes "4 és fél" for speech and "4 1/2" for text

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
    den_str = FRACTION_STRING_HU[den]
    if whole == 0:
        if num == 1:
            one = 'egy ' if den != 2 else ''
            return_string = '{}{}'.format(one, den_str)
        else:
            return_string = '{} {}'.format(num, den_str)
    elif num == 1:
        pointOne = 'egész egy' if den != 2 else 'és'
        return_string = '{} {} {}'.format(whole, pointOne, den_str)
    else:
        return_string = '{} egész {} {}'.format(whole, num, den_str)
    return return_string


def pronounce_number_hu(num, places=2):
    """
    Convert a number to its spoken equivalent

    For example, '5.2' would return 'öt egész két tized'

    Args:
        num(float or int): the number to pronounce (set limit below)
        places(int): maximum decimal places to speak
    Returns:
        (str): The pronounced number
    """

    def pronounce_triplet_hu(num):
        result = ""
        num = floor(num)
        if num > 99:
            hundreds = floor(num / 100)
            if hundreds > 0:
                hundredConst = EXTRA_SPACE + 'száz' + EXTRA_SPACE
                if hundreds == 1:
                    result += hundredConst
                elif hundreds == 2:
                    result += 'két' + hundredConst
                else:
                    result += NUM_STRING_HU[hundreds] + hundredConst
                num -= hundreds * 100
        if num == 0:
            result += ''  # do nothing
        elif num <= 20:
            result += NUM_STRING_HU[num]  # + EXTRA_SPACE
        elif num > 20:
            ones = num % 10
            tens = num - ones
            if tens > 0:
                if tens != 20:
                    result += NUM_STRING_HU[tens] + EXTRA_SPACE
                else:
                    result += "huszon" + EXTRA_SPACE
            if ones > 0:
                result += NUM_STRING_HU[ones] + EXTRA_SPACE
        return result

    def pronounce_whole_number_hu(num, scale_level=0):
        if num == 0:
            return ''

        num = floor(num)
        result = ''
        last_triplet = num % 1000

        if last_triplet == 1:
            if scale_level == 0:
                if result != '':
                    result += '' + "egy"
                else:
                    result += "egy"
            elif scale_level == 1:
                result += EXTRA_SPACE + NUM_POWERS_OF_TEN[1] + EXTRA_SPACE
            else:
                result += "egy" + NUM_POWERS_OF_TEN[scale_level]
        elif last_triplet > 1:
            result += pronounce_triplet_hu(last_triplet)
            if scale_level != 0:
                result = result.replace(NUM_STRING_HU[2], 'két')
            if scale_level == 1:
                result += NUM_POWERS_OF_TEN[1] + EXTRA_SPACE
            if scale_level >= 2:
                result += NUM_POWERS_OF_TEN[scale_level]
            if scale_level > 0:
                result += '-'

        num = floor(num / 1000)
        scale_level += 1
        return pronounce_whole_number_hu(num,
                                         scale_level) + result

    result = ""
    if abs(num) >= 1000000000000000000000000:  # cannot do more than this
        return str(num)
    elif num == 0:
        return str(NUM_STRING_HU[0])
    elif num < 0:
        return "mínusz " + pronounce_number_hu(abs(num), places)
    else:
        if num == int(num):
            return pronounce_whole_number_hu(num).strip('-')
        else:
            whole_number_part = floor(num)
            fractional_part = num - whole_number_part
            if whole_number_part == 0:
                result += NUM_STRING_HU[0]
            result += pronounce_whole_number_hu(whole_number_part)
            if places > 0:
                result += " egész "
                fraction = pronounce_whole_number_hu(
                                        round(fractional_part * 10 ** places))
                result += fraction.replace(NUM_STRING_HU[2], 'két')
                fraction_suffixes = [
                    'tized', 'század', 'ezred', 'tízezred', 'százezred']
                if places <= len(fraction_suffixes):
                    result += ' ' + fraction_suffixes[places - 1]
            return result


def pronounce_ordinal_hu(num):
    ordinals = ["nulladik", "első", "második", "harmadik", "negyedik",
                "ötödik", "hatodik", "hetedik", "nyolcadik", "kilencedik",
                "tizedik"]
    big_ordinals = ["", "ezredik", "milliomodik"]

    # only for whole positive numbers including zero
    if num < 0 or num != int(num):
        return num
    elif num < 11:
        return ordinals[num]
    else:
        # concatenate parts and inflect them accordingly
        root = pronounce_number_hu(num)
        vtype = _get_vocal_type(root)
        last_digit = num - floor(num/10) * 10
        if root == "húsz":
            root = "husz"
        if num % 1000000 == 0:
            return root.replace(NUM_POWERS_OF_TEN[2], big_ordinals[2])
        if num % 1000 == 0:
            return root.replace(NUM_POWERS_OF_TEN[1], big_ordinals[1])
        if last_digit == 1:
            return root + "edik"
        elif root[-1] == 'ő':
            return root[:-1] + 'edik'
        elif last_digit != 0:
            return ordinals[last_digit].join(
                root.rsplit(NUM_STRING_HU[last_digit], 1))
        return root + "edik" if vtype == 1 else root + "adik"


def nice_time_hu(dt, speech=True, use_24hour=False, use_ampm=False):
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
        speak += pronounce_number_hu(dt.hour)
        speak = speak.replace(NUM_STRING_HU[2], 'két')
        speak += " óra"
        if not dt.minute == 0:  # zero minutes are not pronounced
            speak += " " + pronounce_number_hu(dt.minute)

        return speak  # ampm is ignored when use_24hour is true
    else:
        if dt.hour == 0 and dt.minute == 0:
            return "éjfél"
        if dt.hour == 12 and dt.minute == 0:
            return "dél"
        # TODO: "half past 3", "a quarter of 4" and other idiomatic times

        if dt.hour == 0:
            speak += pronounce_number_hu(12)
        elif dt.hour < 13:
            speak = pronounce_number_hu(dt.hour)
        else:
            speak = pronounce_number_hu(dt.hour - 12)

        speak = speak.replace(NUM_STRING_HU[2], 'két')
        speak += " óra"

        if not dt.minute == 0:
            speak += " " + pronounce_number_hu(dt.minute)

        if use_ampm:
            if dt.hour > 11:
                if dt.hour < 18:
                    speak = "délután " + speak  # 12:01 - 17:59
                elif dt.hour < 22:
                    speak = "este " + speak  # 18:00 - 21:59 este/evening
                else:
                    speak = "éjjel " + speak  # 22:00 - 23:59 éjjel/at night
            elif dt.hour < 3:
                speak = "éjjel " + speak  # 00:01 - 02:59 éjjel/at night
            else:
                speak = "reggel " + speak  # 03:00 - 11:59 reggel/in t. morning

        return speak
