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
import collections


NUM_STRING_EN = {
    0: 'zero',
    1: 'one',
    2: 'two',
    3: 'three',
    4: 'four',
    5: 'five',
    6: 'six',
    7: 'seven',
    8: 'eight',
    9: 'nine',
    10: 'ten',
    11: 'eleven',
    12: 'twelve',
    13: 'thirteen',
    14: 'fourteen',
    15: 'fifteen',
    16: 'sixteen',
    17: 'seventeen',
    18: 'eighteen',
    19: 'nineteen',
    20: 'twenty',
    30: 'thirty',
    40: 'forty',
    50: 'fifty',
    60: 'sixty',
    70: 'seventy',
    80: 'eighty',
    90: 'ninety'
}

FRACTION_STRING_EN = {
    2: 'half',
    3: 'third',
    4: 'forth',
    5: 'fifth',
    6: 'sixth',
    7: 'seventh',
    8: 'eigth',
    9: 'ninth',
    10: 'tenth',
    11: 'eleventh',
    12: 'twelveth',
    13: 'thirteenth',
    14: 'fourteenth',
    15: 'fifteenth',
    16: 'sixteenth',
    17: 'seventeenth',
    18: 'eighteenth',
    19: 'nineteenth',
    20: 'twentyith'
}

LONG_SCALE_EN = collections.OrderedDict([
    (10e1, 'hundred'),
    (10e3, 'thousand'),
    (10e6, 'million'),
    (10e12, "billion"),
    (10e18, 'trillion'),
    (10e24, "quadrillion"),
    (10e30, "quintillion"),
    (10e36, "sextillion"),
    (10e42, "septillion"),
    (10e48, "octillion"),
    (10e54, "nonillion"),
    (10e60, "decillion"),
    (10e66, "undecillion"),
    (10e72, "duodecillion"),
    (10e78, "tredecillion"),
    (10e84, "quattuordecillion"),
    (10e90, "quinquadecillion"),
    (10e96, "sedecillion"),
    (10e102, "septendecillion"),
    (10e108, "octodecillion"),
    (10e114, "novendecillion"),
    (10e120, "vigintillion"),
    (10e306, "unquinquagintillion"),
    (10e312, "duoquinquagintillion"),
    (10e336, "sesquinquagintillion"),
    (10e366, "unsexagintillion"),
    (10e100, "googol")
])

SHORT_SCALE_EN = collections.OrderedDict([
    (10e1, 'hundred'),
    (10e3, 'thousand'),
    (10e6, 'million'),
    (10e9, "billion"),
    (10e12, 'trillion'),
    (10e15, "quadrillion"),
    (10e18, "quintillion"),
    (10e21, "sextillion"),
    (10e24, "septillion"),
    (10e27, "octillion"),
    (10e30, "nonillion"),
    (10e33, "decillion"),
    (10e36, "undecillion"),
    (10e39, "duodecillion"),
    (10e42, "tredecillion"),
    (10e45, "quattuordecillion"),
    (10e48, "quinquadecillion"),
    (10e51, "sedecillion"),
    (10e54, "septendecillion"),
    (10e57, "octodecillion"),
    (10e60, "novendecillion"),
    (10e63, "vigintillion"),
    (10e66, "unvigintillion"),
    (10e69, "uuovigintillion"),
    (10e72, "tresvigintillion"),
    (10e75, "quattuorvigintillion"),
    (10e78, "quinquavigintillion"),
    (10e81, "qesvigintillion"),
    (10e84, "septemvigintillion"),
    (10e87, "octovigintillion"),
    (10e90, "novemvigintillion"),
    (10e93, "trigintillion"),
    (10e96, "untrigintillion"),
    (10e99, "duotrigintillion"),
    (10e102, "trestrigintillion"),
    (10e105, "quattuortrigintillion"),
    (10e108, "quinquatrigintillion"),
    (10e111, "sestrigintillion"),
    (10e114, "septentrigintillion"),
    (10e117, "octotrigintillion"),
    (10e120, "noventrigintillion"),
    (10e123, "quadragintillion"),
    (10e153, "quinquagintillion"),
    (10e183, "sexagintillion"),
    (10e213, "septuagintillion"),
    (10e243, "octogintillion"),
    (10e273, "nonagintillion"),
    (10e303, "centillion"),
    (10e306, "uncentillion"),
    (10e309, "duocentillion"),
    (10e312, "trescentillion"),
    (10e333, "decicentillion"),
    (10e336, "undecicentillion"),
    (10e363, "viginticentillion"),
    (10e366, "unviginticentillion"),
    (10e393, "trigintacentillion"),
    (10e423, "quadragintacentillion"),
    (10e453, "quinquagintacentillion"),
    (10e483, "sexagintacentillion"),
    (10e513, "septuagintacentillion"),
    (10e543, "ctogintacentillion"),
    (10e573, "nonagintacentillion"),
    (10e603, "ducentillion"),
    (10e903, "trecentillion"),
    (10e1203, "quadringentillion"),
    (10e1503, "quingentillion"),
    (10e1803, "sescentillion"),
    (10e2103, "septingentillion"),
    (10e2403, "octingentillion"),
    (10e2703, "nongentillion"),
    (10e3003, "millinillion"),
    (10e100, "googol")
])


def nice_number_en(number, speech, denominators):
    """ English helper for nice_number

    This function formats a float to human understandable functions. Like
    4.5 becomes "4 and a half" for speech and "4 1/2" for text

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
        return str(round(number, 3))

    whole, num, den = result

    if not speech:
        if num == 0:
            # TODO: Number grouping?  E.g. "1,000,000"
            return str(whole)
        else:
            return '{} {}/{}'.format(whole, num, den)

    if num == 0:
        return str(whole)
    den_str = FRACTION_STRING_EN[den]
    if whole == 0:
        if num == 1:
            return_string = 'a {}'.format(den_str)
        else:
            return_string = '{} {}'.format(num, den_str)
    elif num == 1:
        return_string = '{} and a {}'.format(whole, den_str)
    else:
        return_string = '{} and {} {}'.format(whole, num, den_str)
    if num > 1:
        return_string += 's'
    return return_string


def pronounce_number_en(num, places=2, short_scale=False):
    """
    Convert a number to it's spoken equivalent

    For example, '5.2' would return 'five point two'

    Args:
        num(float or int): the number to pronounce (under 100)
        places(int): maximum decimal places to speak
    Returns:
        (str): The pronounced number
    """
    number_names = {**NUM_STRING_EN, **LONG_SCALE_EN} if not short_scale \
        else {**NUM_STRING_EN, **SHORT_SCALE_EN}

    digits = [number_names[n] for n in range(0, 20)]

    tens = [number_names[n] for n in range(10, 100, 10)]

    if short_scale:
        hundreds = [SHORT_SCALE_EN[n] for n in SHORT_SCALE_EN.keys()]
    else:
        hundreds = [LONG_SCALE_EN[n] for n in LONG_SCALE_EN.keys()]

    # deal with negatives
    result = ""
    if num < 0:
        result = "negative "
    num = abs(num)

    # check for a direct match
    if num in number_names:
        if num > 90:
            result += "one "
        result += number_names[num]
    else:
        def _sub_thousand(n):
            assert (0 <= n <= 999)
            if n <= 19:
                return digits[n]
            elif n <= 99:
                q, r = divmod(n, 10)
                return tens[q - 1] + (" " + _sub_thousand(r) if r else "")
            else:
                q, r = divmod(n, 100)
                return digits[q] + " hundred" + (
                    " and " + _sub_thousand(r) if r else "")

        def _short_scale(n):
            n = int(n)
            assert (0 <= n)
            return ", ".join(reversed(
                [_sub_thousand(z) + (
                    " " + hundreds[i] if i else "") if z else ""
                 for i, z in enumerate(_split_by_thousands(n))]))

        def _split_by_thousands(n):
            assert (0 <= n)
            res = []
            while n:
                n, r = divmod(n, 1000)
                res.append(r)
            return res

        if short_scale:
            result += _short_scale(num)
        else:
            # TODO long scale
            result += _short_scale(num)

    # Deal with fractional part
    if not num == int(num) and places > 0:
        result += " point"
        place = 10
        while int(num * place) % 10 > 0 and places > 0:
            result += " " + number_names[int(num * place) % 10]
            place *= 10
            places -= 1
    return result


def nice_time_en(dt, speech=True, use_24hour=False, use_ampm=False):
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
    if use_24hour:
        speak = ""

        # Either "0 8 hundred" or "13 hundred"
        if string[0] == '0':
            speak += pronounce_number_en(int(string[0])) + " "
            speak += pronounce_number_en(int(string[1]))
        else:
            speak = pronounce_number_en(int(string[0:2]))

        speak += " "
        if string[3:5] == '00':
            speak += "hundred"
        else:
            if string[3] == '0':
                speak += pronounce_number_en(0) + " "
                speak += pronounce_number_en(int(string[4]))
            else:
                speak += pronounce_number_en(int(string[3:5]))
        return speak
    else:
        if dt.hour == 0 and dt.minute == 0:
            return "midnight"
        if dt.hour == 12 and dt.minute == 0:
            return "noon"
        # TODO: "half past 3", "a quarter of 4" and other idiomatic times

        if dt.hour == 0:
            speak = pronounce_number_en(12)
        elif dt.hour < 13:
            speak = pronounce_number_en(dt.hour)
        else:
            speak = pronounce_number_en(dt.hour - 12)

        if dt.minute == 0:
            if not use_ampm:
                return speak + " o'clock"
        else:
            if dt.minute < 10:
                speak += " oh"
            speak += " " + pronounce_number_en(dt.minute)

        if use_ampm:
            if dt.hour > 11:
                speak += " PM"
            else:
                speak += " AM"

        return speak
