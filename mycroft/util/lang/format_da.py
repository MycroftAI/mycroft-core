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

months = ['januar', 'februar', 'märz', 'april', 'mai', 'juni',
          'juli', 'august', 'september', 'oktober', 'november',
          'dezember']

NUM_STRING_DA = {
    0: 'nul',
    1: 'en',
    2: 'to',
    3: 'tre',
    4: 'fire',
    5: 'fem',
    6: 'seks',
    7: 'syv',
    8: 'otte',
    9: 'ni',
    10: 'ti',
    11: 'elve',
    12: 'tolv',
    13: 'tretten',
    14: 'fjorten',
    15: 'femten',
    16: 'seksten',
    17: 'sytten',
    18: 'atten',
    19: 'nitten',
    20: 'tyve',
    30: 'tredive',
    40: 'fyrre',
    50: 'halvtres',
    60: 'tres',
    70: 'halvfjers',
    80: 'firs',
    90: 'halvfems',
    100: 'hundrede'
}

NUM_POWERS_OF_TEN = [
    'hundred',
    'tusind',
    'million',
    'milliard',
    'billion',
    'billiard',
    'trillion',
    'trilliard'
]

FRACTION_STRING_DA = {
    2: 'halv',
    3: 'trediedel',
    4: 'fjerdedel',
    5: 'femtedel',
    6: 'sjettedel',
    7: 'syvendedel',
    8: 'ottendedel',
    9: 'niendedel',
    10: 'tiendedel',
    11: 'elftedel',
    12: 'tolvtedel',
    13: 'trettendedel',
    14: 'fjortendedel',
    15: 'femtendedel',
    16: 'sejstendedel',
    17: 'syttendedel',
    18: 'attendedel',
    19: 'nittendedel',
    20: 'tyvendedel'
}

# Numbers below 1 million are written in one word in German, yielding very
# long words
# In some circumstances it may better to seperate individual words
# Set EXTRA_SPACE=" " for separating numbers below 1 million (
# orthographically incorrect)
# Set EXTRA_SPACE="" for correct spelling, this is standard

# EXTRA_SPACE = " "
EXTRA_SPACE = ""


def nice_number_da(number, speech, denominators):
    """ Danish helper for nice_number
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
    den_str = FRACTION_STRING_DA[den]
    if whole == 0:
        if num == 1:
            return_string = '{} {}'.format(num, den_str)
        else:
            return_string = '{} {}e'.format(num, den_str)
    else:
        if num == 1:
            return_string = '{} og {} {}'.format(whole, num, den_str)
        else:
            return_string = '{} og {} {}e'.format(whole, num, den_str)

    return return_string


def pronounce_number_da(num, places=2):
    """
    Convert a number to its spoken equivalent
    For example, '5.2' would return 'five point two'
    Args:
        num(float or int): the number to pronounce (set limit below)
        places(int): maximum decimal places to speak
    Returns:
        (str): The pronounced number

    """

    def pronounce_triplet_da(num):
        result = ""
        num = floor(num)
        if num > 99:
            hundreds = floor(num / 100)
            if hundreds > 0:
                if hundreds == 1:
                    result += 'et' + 'hundrede' + EXTRA_SPACE
                else:
                    result += NUM_STRING_DA[hundreds] + \
                        'hundrede' + EXTRA_SPACE
                    num -= hundreds * 100
        if num == 0:
            result += ''  # do nothing
        elif num == 1:
            result += 'et'
        elif num <= 20:
            result += NUM_STRING_DA[num] + EXTRA_SPACE
        elif num > 20:
            ones = num % 10
            tens = num - ones
            if ones > 0:
                result += NUM_STRING_DA[ones] + EXTRA_SPACE
                if tens > 0:
                    result += 'og' + EXTRA_SPACE
            if tens > 0:
                result += NUM_STRING_DA[tens] + EXTRA_SPACE

        return result

    def pronounce_fractional_da(num, places):
        # fixed number of places even with trailing zeros
        result = ""
        place = 10
        while places > 0:
            # doesn't work with 1.0001 and places = 2: int(
            # num*place) % 10 > 0 and places > 0:
            result += " " + NUM_STRING_DA[int(num * place) % 10]
            place *= 10
            places -= 1
        return result

    def pronounce_whole_number_da(num, scale_level=0):
        if num == 0:
            return ''

        num = floor(num)
        result = ''
        last_triplet = num % 1000

        if last_triplet == 1:
            if scale_level == 0:
                if result != '':
                    result += '' + 'et'
                else:
                    result += "en"
            elif scale_level == 1:
                result += 'et' + EXTRA_SPACE + 'tusinde' + EXTRA_SPACE
            else:
                result += "en " + NUM_POWERS_OF_TEN[scale_level] + ' '
        elif last_triplet > 1:
            result += pronounce_triplet_da(last_triplet)
            if scale_level == 1:
                result += 'tusinde' + EXTRA_SPACE
            if scale_level >= 2:
                result += "og" + NUM_POWERS_OF_TEN[scale_level]
            if scale_level >= 2:
                if scale_level % 2 == 0:
                    result += "er"  # MillionER
                result += "er "  # MilliardER, MillioneER

        num = floor(num / 1000)
        scale_level += 1
        return pronounce_whole_number_da(num,
                                         scale_level) + result + EXTRA_SPACE

    result = ""
    if abs(num) >= 1000000000000000000000000:  # cannot do more than this
        return str(num)
    elif num == 0:
        return str(NUM_STRING_DA[0])
    elif num < 0:
        return "minus " + pronounce_number_da(abs(num), places)
    else:
        if num == int(num):
            return pronounce_whole_number_da(num)
        else:
            whole_number_part = floor(num)
            fractional_part = num - whole_number_part
            result += pronounce_whole_number_da(whole_number_part)
            if places > 0:
                result += " komma"
                result += pronounce_fractional_da(fractional_part, places)
            return result


def pronounce_ordinal_da(num):
    # ordinals for 1, 3, 7 and 8 are irregular
    # this produces the base form, it will have to be adapted for genus,
    # casus, numerus

    ordinals = ["nulte", "første", "anden", "tredie", "fjerde", "femte",
                "sjette", "syvende", "ottende", "niende", "tiende"]

    # only for whole positive numbers including zero
    if num < 0 or num != int(num):
        return num
    if num < 10:
        return ordinals[num]
    if num < 30:
        if pronounce_number_da(num)[-1:] == 'e':
            return pronounce_number_da(num) + "nde"
        else:
            return pronounce_number_da(num) + "ende"
    if num < 40:
        return pronounce_number_da(num) + "fte"
    else:
        if pronounce_number_da(num)[-1:] == 'e':
            return pronounce_number_da(num) + "nde"
        else:
            return pronounce_number_da(num) + "ende"


def nice_time_da(dt, speech=True, use_24hour=False, use_ampm=False):
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

    if not speech:
        return string

    # Generate a speakable version of the time
    speak = ""
    if use_24hour:
        if dt.hour == 1:
            speak += "et"  # 01:00 is "et" not "en"
        else:
            speak += pronounce_number_da(dt.hour)
        if not dt.minute == 0:
            if dt.minute < 10:
                speak += ' nul'
            speak += " " + pronounce_number_da(dt.minute)

        return speak  # ampm is ignored when use_24hour is true
    else:
        if dt.hour == 0 and dt.minute == 0:
            return "midnat"
        if dt.hour == 12 and dt.minute == 0:
            return "middag"
        # TODO: "half past 3", "a quarter of 4" and other idiomatic times

        if dt.hour == 0:
            speak += pronounce_number_da(12)
        elif dt.hour <= 13:
            if dt.hour == 1 or dt.hour == 13:  # 01:00 and 13:00 is "et"
                speak += 'et'
            else:
                speak += pronounce_number_da(dt.hour)
        else:
            speak += pronounce_number_da(dt.hour - 12)

        if not dt.minute == 0:
            if dt.minute < 10:
                speak += ' nul'
            speak += " " + pronounce_number_da(dt.minute)

        if use_ampm:
            if dt.hour > 11:
                if dt.hour < 18:
                    # 12:01 - 17:59 nachmittags/afternoon
                    speak += " om eftermiddagen"
                elif dt.hour < 22:
                    # 18:00 - 21:59 abends/evening
                    speak += " om aftenen"
                else:
                    # 22:00 - 23:59 nachts/at night
                    speak += " om natten"
            elif dt.hour < 3:
                # 00:01 - 02:59 nachts/at night
                speak += " om natten"
            else:
                # 03:00 - 11:59 morgens/in the morning
                speak += " om morgenen"

        return speak


def nice_response_da(text):
    # check for months and call nice_ordinal_da declension of ordinals
    # replace "^" with "hoch" (to the power of)
    words = text.split()

    for idx, word in enumerate(words):
        if word.lower() in months:
            text = nice_ordinal_da(text)

        if word == '^':
            wordNext = words[idx + 1] if idx + 1 < len(words) else ""
            if wordNext.isnumeric():
                words[idx] = "opløftet i"
                text = " ".join(words)
    return text


def nice_ordinal_da(text):
    # check for months for declension of ordinals before months
    # depending on articles/prepositions
    normalized_text = text
    words = text.split()

    for idx, word in enumerate(words):
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        if word[-1:] == ".":
            if word[:-1].isdecimal():
                if wordNext.lower() in months:
                    word = pronounce_ordinal_da(int(word[:-1]))
                    if wordPrev.lower() in ["om", "den", "fra", "til",
                                            "(fra", "(om", "til"]:
                        word += "n"
                    elif wordPrev.lower() not in ["den"]:
                        word += "r"
                    words[idx] = word
            normalized_text = " ".join(words)
    return normalized_text
