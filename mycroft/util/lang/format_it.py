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

NUM_STRING_IT = {
    0: 'zero',
    1: 'uno',
    2: 'due',
    3: 'tre',
    4: 'quattro',
    5: 'cinque',
    6: 'sei',
    7: 'sette',
    8: 'otto',
    9: 'nove',
    10: 'dieci',
    11: 'undici',
    12: 'dodici',
    13: 'tredici',
    14: 'quattordici',
    15: 'quindici',
    16: 'sedici',
    17: 'diciassette',
    18: 'diciotto',
    19: 'diciannove',
    20: 'venti',
    30: 'trenta',
    40: 'quaranta',
    50: 'cinquanta',
    60: 'sessanta',
    70: 'settanta',
    80: 'ottanta',
    90: 'novanta'
}

FRACTION_STRING_IT = {
    2: 'mezz',
    3: 'terz',
    4: 'quart',
    5: 'quint',
    6: 'sest',
    7: 'settim',
    8: 'ottav',
    9: 'non',
    10: 'decim',
    11: 'undicesim',
    12: 'dodicesim',
    13: 'tredicesim',
    14: 'quattordicesim',
    15: 'quindicesim',
    16: 'sedicesim',
    17: 'diciassettesim',
    18: 'diciottesim',
    19: 'diciannovesim',
    20: 'ventesim'
}


def nice_number_it(number, speech, denominators):
    """ Italian helper for nice_number

    This function formats a float to human understandable functions. Like
    4.5 becomes "4 e un mezz" for speech and "4 1/2" for text

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
    # denominatore
    den_str = FRACTION_STRING_IT[den]
    # frazione
    if whole == 0:
        if num == 1:
            # un decimo
            return_string = 'un {}'.format(den_str)
        else:
            # tre mezzi
            return_string = '{} {}'.format(num, den_str)
    # interi  >10
    elif num == 1:
        # trenta e un
        return_string = '{} e un {}'.format(whole, den_str)
    # interi >10 con frazioni
    else:
        # venti e 3 decimi
        return_string = '{} e {} {}'.format(whole, num, den_str)

    # gestisce il plurale del denominatore
    if num > 1:
        return_string += 'i'
    else:
        return_string += 'o'

    return return_string


def pronounce_number_it(num, places=2):
    """
    Convert a number to it's spoken equivalent
    adapted to italian fron en version

    For example, '5.2' would return 'cinque virgola due'

    Args:
        num(float or int): the number to pronounce (under 100)
        places(int): maximum decimal places to speak
    Returns:
        (str): The pronounced number
    """
    if abs(num) >= 100:
        # TODO: Support for numbers over 100
        return str(num)

    result = ""
    if num < 0:
        result = "meno "
    num = abs(num)

    if num > 20:
        tens = int(num-int(num) % 10)
        ones = int(num - tens)
        result += NUM_STRING_IT[tens]
        if ones > 0:
            if ones == 1 or ones == 8:
                result = result[:-1]  # ventuno  ventotto
            result += NUM_STRING_IT[ones]

    else:
        result += NUM_STRING_IT[int(num)]

    # Deal with fractional part
    if not num == int(num) and places > 0:
        result += " virgola"
        place = 10
        while int(num*place) % 10 > 0 and places > 0:
            result += " " + NUM_STRING_IT[int(num*place) % 10]
            place *= 10
            places -= 1
    return result


def nice_time_it(dt, speech=True, use_24hour=False, use_ampm=False):
    """
    Format a time to a comfortable human format
    adapted to italian fron en version

    For example, generate 'cinque e trenta' for speech or '5:30' for
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
        # Either "zero 8 zerozero" o "13 zerozero"
        if string[0:2] == '00':
            speak += "zerozero"
        elif string[0] == '0':
            speak += pronounce_number_it(int(string[0])) + " "
            if int(string[1]) == 1:
                speak += "una"  # TODO: valutare forma "l'una"
            else:
                speak += pronounce_number_it(int(string[1]))
        else:
            speak = pronounce_number_it(int(string[0:2]))

        # in italian  "13 e 25"
        speak += " e "

        if string[3:5] == '00':
            speak += "zerozero"
        else:
            if string[3] == '0':
                speak += pronounce_number_it(0) + " "
                speak += pronounce_number_it(int(string[4]))
            else:
                speak += pronounce_number_it(int(string[3:5]))
        return speak
    else:
        if dt.hour == 0 and dt.minute == 0:
            return "mezzanotte"
        if dt.hour == 12 and dt.minute == 0:
            return "mezzogiorno"
        # TODO: "10 e un quarto", "4 e tre quarti" and ot her idiomatic times

        if dt.hour == 0:
            speak = "mezzanotte"
        elif dt.hour == 1 or dt.hour == 13:
            speak = "una"
        elif dt.hour > 13:  # era minore
            speak = pronounce_number_it(dt.hour-12)
        else:
            speak = pronounce_number_it(dt.hour-12)

        speak += " e"
        if dt.minute == 0:
            speak = speak[:-2]
            if not use_ampm:
                speak += " in punto"
        else:
            if dt.minute < 10:
                speak += " zero"
            speak += " " + pronounce_number_it(dt.minute)

        if use_ampm:

            if dt.hour < 4:
                speak.strip()
            elif dt.hour > 12:
                speak += " del pomeriggio"
            elif dt.hour > 17:
                speak += " della sera"
            elif dt.hour > 20:
                speak += " della notte"
            else:
                speak += " della mattina"

        return speak
