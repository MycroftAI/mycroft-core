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
""" Format functions for french (fr)

"""

from mycroft.util.lang.format_common import convert_to_mixed_fraction

NUM_STRING_FR = {
    0: 'zéro',
    1: 'un',
    2: 'deux',
    3: 'trois',
    4: 'quatre',
    5: 'cinq',
    6: 'six',
    7: 'sept',
    8: 'huit',
    9: 'neuf',
    10: 'dix',
    11: 'onze',
    12: 'douze',
    13: 'treize',
    14: 'quatorze',
    15: 'quinze',
    16: 'seize',
    20: 'vingt',
    30: 'trente',
    40: 'quarante',
    50: 'cinquante',
    60: 'soixante',
    70: 'soixante-dix',
    80: 'quatre-vingt',
    90: 'quatre-vingt-dix'
}

FRACTION_STRING_FR = {
    2: 'demi',
    3: 'tiers',
    4: 'quart',
    5: 'cinquième',
    6: 'sixième',
    7: 'septième',
    8: 'huitième',
    9: 'neuvième',
    10: 'dixième',
    11: 'onzième',
    12: 'douzième',
    13: 'treizième',
    14: 'quatorzième',
    15: 'quinzième',
    16: 'seizième',
    17: 'dix-septième',
    18: 'dix-huitième',
    19: 'dix-neuvième',
    20: 'vingtième'
}


def nice_number_fr(number, speech, denominators):
    """ French helper for nice_number

    This function formats a float to human understandable functions. Like
    4.5 becomes "4 et demi" for speech and "4 1/2" for text

    Args:
        number (int or float): the float to format
        speech (bool): format for speech (True) or display (False)
        denominators (iter of ints): denominators to use, default [1 .. 20]
    Returns:
        (str): The formatted string.
    """
    strNumber = ""
    whole = 0
    num = 0
    den = 0

    result = convert_to_mixed_fraction(number, denominators)

    if not result:
        # Give up, just represent as a 3 decimal number
        whole = round(number, 3)
    else:
        whole, num, den = result

    if not speech:
        if num == 0:
            strNumber = '{:,}'.format(whole)
            strNumber = strNumber.replace(",", " ")
            strNumber = strNumber.replace(".", ",")
            return strNumber
        else:
            return '{} {}/{}'.format(whole, num, den)
    else:
        if num == 0:
            # if the number is not a fraction, nothing to do
            strNumber = str(whole)
            strNumber = strNumber.replace(".", ",")
            return strNumber
        den_str = FRACTION_STRING_FR[den]
        # if it is not an integer
        if whole == 0:
            # if there is no whole number
            if num == 1:
                # if numerator is 1, return "un demi", for example
                strNumber = 'un {}'.format(den_str)
            else:
                # else return "quatre tiers", for example
                strNumber = '{} {}'.format(num, den_str)
        elif num == 1:
            # if there is a whole number and numerator is 1
            if den == 2:
                # if denominator is 2, return "1 et demi", for example
                strNumber = '{} et {}'.format(whole, den_str)
            else:
                # else return "1 et 1 tiers", for example
                strNumber = '{} et 1 {}'.format(whole, den_str)
        else:
            # else return "2 et 3 quart", for example
            strNumber = '{} et {} {}'.format(whole, num, den_str)
        if num > 1 and den != 3:
            # if the numerator is greater than 1 and the denominator
            # is not 3 ("tiers"), add an s for plural
            strNumber += 's'

    return strNumber


def pronounce_number_fr(num, places=2):
    """
    Convert a number to it's spoken equivalent

    For example, '5.2' would return 'cinq virgule deux'

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
        result = "moins "
    num = abs(num)

    if num > 16:
        tens = int(num-int(num) % 10)
        ones = int(num-tens)
        if ones != 0:
            if tens > 10 and tens <= 60 and int(num-tens) == 1:
                result += NUM_STRING_FR[tens] + "-et-" + NUM_STRING_FR[ones]
            elif num == 71:
                result += "soixante-et-onze"
            elif tens == 70:
                result += NUM_STRING_FR[60] + "-"
                if ones < 7:
                    result += NUM_STRING_FR[10 + ones]
                else:
                    result += NUM_STRING_FR[10] + "-" + NUM_STRING_FR[ones]
            elif tens == 90:
                result += NUM_STRING_FR[80] + "-"
                if ones < 7:
                    result += NUM_STRING_FR[10 + ones]
                else:
                    result += NUM_STRING_FR[10] + "-" + NUM_STRING_FR[ones]
            else:
                result += NUM_STRING_FR[tens] + "-" + NUM_STRING_FR[ones]
        else:
            if num == 80:
                result += "quatre-vingts"
            else:
                result += NUM_STRING_FR[tens]
    else:
        result += NUM_STRING_FR[int(num)]

    # Deal with decimal part
    if not num == int(num) and places > 0:
        result += " virgule"
        place = 10
        while int(num*place) % 10 > 0 and places > 0:
            result += " " + NUM_STRING_FR[int(num*place) % 10]
            place *= 10
            places -= 1
    return result


def nice_time_fr(dt, speech=True, use_24hour=False, use_ampm=False):
    """
    Format a time to a comfortable human format

    For example, generate 'cinq heures trente' for speech or '5:30' for
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

        # "13 heures trente"
        if dt.hour == 0:
            speak += "minuit"
        elif dt.hour == 12:
            speak += "midi"
        elif dt.hour == 1:
            speak += "une heure"
        else:
            speak += pronounce_number_fr(dt.hour) + " heures"

        if dt.minute != 0:
            speak += " " + pronounce_number_fr(dt.minute)

    else:
        # Prepare for "trois heures moins le quart"
        if dt.minute == 35:
            minute = -25
            hour = dt.hour + 1
        elif dt.minute == 40:
            minute = -20
            hour = dt.hour + 1
        elif dt.minute == 45:
            minute = -15
            hour = dt.hour + 1
        elif dt.minute == 50:
            minute = -10
            hour = dt.hour + 1
        elif dt.minute == 55:
            minute = -5
            hour = dt.hour + 1
        else:
            minute = dt.minute
            hour = dt.hour

        if hour == 0:
            speak += "minuit"
        elif hour == 12:
            speak += "midi"
        elif hour == 1 or hour == 13:
            speak += "une heure"
        elif hour < 13:
            speak = pronounce_number_fr(hour) + " heures"
        else:
            speak = pronounce_number_fr(hour-12) + " heures"

        if minute != 0:
            if minute == 15:
                speak += " et quart"
            elif minute == 30:
                speak += " et demi"
            elif minute == -15:
                speak += " moins le quart"
            else:
                speak += " " + pronounce_number_fr(minute)

        if use_ampm:
            if hour > 17:
                speak += " du soir"
            elif hour > 12:
                speak += " de l'après-midi"
            elif hour > 0 and hour < 12:
                speak += " du matin"

    return speak
