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

# fonte: http://tulengua.es/numeros-texto/default.aspx
LONG_SCALE_IT = collections.OrderedDict([
    (100, 'cento'),
    (1000, 'mila'),
    (1000000, 'milioni'),
    (1e9, "miliardi"),
    (1e12, "bilioni"),
    (1e18, 'trilioni'),
    (1e24, "quadrilioni"),
    (1e30, "quintilioni"),
    (1e36, "sestilioni"),
    (1e42, "settilioni"),
    (1e48, "ottillioni"),
    (1e54, "nonillioni"),
    (1e60, "decemillioni"),
    (1e66, "undicilione"),
    (1e72, "dodicilione"),
    (1e78, "tredicilione"),
    (1e84, "quattordicilione"),
    (1e90, "quindicilione"),
    (1e96, "sedicilione"),
    (1e102, "diciasettilione"),
    (1e108, "diciottilione"),
    (1e114, "dicianovilione"),
    (1e120, "vintilione"),
    (1e306, "unquinquagintilione"),
    (1e312, "duoquinquagintilione"),
    (1e336, "sesquinquagintilione"),
    (1e366, "unsexagintilione")
])


SHORT_SCALE_IT = collections.OrderedDict([
    (100, 'cento'),
    (1000, 'mila'),
    (1000000, 'milioni'),
    (1e9, "miliardi"),
    (1e12, 'bilioni'),
    (1e15, "biliardi"),
    (1e18, "trilioni"),
    (1e21, "triliardi"),
    (1e24, "quadrilioni"),
    (1e27, "quadriliardi"),
    (1e30, "quintilioni"),
    (1e33, "quintiliardi"),
    (1e36, "sestilioni"),
    (1e39, "sestiliardi"),
    (1e42, "settilioni"),
    (1e45, "settiliardi"),
    (1e48, "ottilioni"),
    (1e51, "ottiliardi"),
    (1e54, "nonilioni"),
    (1e57, "noniliardi"),
    (1e60, "decilioni"),
    (1e63, "deciliardi"),
    (1e66, "undicilioni"),
    (1e69, "undiciliardi"),
    (1e72, "dodicilioni"),
    (1e75, "dodiciliardi"),
    (1e78, "tredicilioni"),
    (1e81, "trediciliardi"),
    (1e84, "quattordicilioni"),
    (1e87, "quattordiciliardi"),
    (1e90, "quindicilioni"),
    (1e93, "quindiciliardi"),
    (1e96, "sedicilioni"),
    (1e99, "sediciliardi"),
    (1e102, "diciassettilioni"),
    (1e105, "diciassettiliardi"),
    (1e108, "diciottilioni"),
    (1e111, "diciottiliardi"),
    (1e114, "dicianovilioni"),
    (1e117, "dicianoviliardi"),
    (1e120, "vintilioni"),
    (1e123, "vintiliardi"),
    (1e153, "quinquagintillion"),
    (1e183, "sexagintillion"),
    (1e213, "septuagintillion"),
    (1e243, "ottogintilioni"),
    (1e273, "nonigintillioni"),
    (1e303, "centilioni"),
    (1e306, "uncentilioni"),
    (1e309, "duocentilioni"),
    (1e312, "trecentilioni"),
    (1e333, "decicentilioni"),
    (1e336, "undicicentilioni"),
    (1e363, "viginticentilioni"),
    (1e366, "unviginticentilioni"),
    (1e393, "trigintacentilioni"),
    (1e423, "quadragintacentillion"),
    (1e453, "quinquagintacentillion"),
    (1e483, "sexagintacentillion"),
    (1e513, "septuagintacentillion"),
    (1e543, "ctogintacentillion"),
    (1e573, "nonagintacentillion"),
    (1e603, "ducentillion"),
    (1e903, "trecentillion"),
    (1e1203, "quadringentillion"),
    (1e1503, "quingentillion"),
    (1e1803, "sescentillion"),
    (1e2103, "septingentillion"),
    (1e2403, "octingentillion"),
    (1e2703, "nongentillion"),
    (1e3003, "millinillion")
])


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


def pronounce_number_it(num, places=2, short_scale=False, scientific=False):
    """
    Convert a number to it's spoken equivalent
    adapted to italian fron en version

    For example, '5.2' would return 'cinque virgola due'

    Args:
        num(float or int): the number to pronounce (under 100)
        places(int): maximum decimal places to speak
        short_scale (bool) : use short (True) or long scale (False)
            https://en.wikipedia.org/wiki/Names_of_large_numbers
        scientific (bool): pronounce in scientific notation
    Returns:
        (str): The pronounced number
    """
    # gestione infinito
    if num == float("inf"):
        return "infinito"
    elif num == float("-inf"):
        return "meno infinito"

    if scientific:
        number = '%E' % num
        n, power = number.replace("+", "").split("E")
        power = int(power)
        if power != 0:
            return '{}{} per dieci elevato alla {}{}'.format(
                'meno ' if float(n) < 0 else '',
                pronounce_number_it(abs(float(n)), places, short_scale, False),
                'meno ' if power < 0 else '',
                pronounce_number_it(abs(power), places, short_scale, False))

    if short_scale:
        number_names = NUM_STRING_IT.copy()
        number_names.update(SHORT_SCALE_IT)
    else:
        number_names = NUM_STRING_IT.copy()
        number_names.update(LONG_SCALE_IT)

    digits = [number_names[n] for n in range(0, 20)]

    tens = [number_names[n] for n in range(10, 100, 10)]

    if short_scale:
        hundreds = [SHORT_SCALE_IT[n] for n in SHORT_SCALE_IT.keys()]
    else:
        hundreds = [LONG_SCALE_IT[n] for n in LONG_SCALE_IT.keys()]

    # deal with negatives
    result = ""
    if num < 0:
        result = "meno "
    num = abs(num)

    # check for a direct match
    if num in number_names:
        if num > 90:
            result += ""  # inizio stringa
        result += number_names[num]
    else:
        def _sub_thousand(n):
            assert 0 <= n <= 999
            if n <= 19:
                return digits[n]
            elif n <= 99:
                q, r = divmod(n, 10)
                _deci = tens[q-1]
                _unit = r
                _partial = _deci
                if _unit > 0:
                    if _unit == 1 or _unit == 8:
                        _partial = _partial[:-1]  # ventuno  ventotto
                    _partial += number_names[_unit]
                return _partial
            else:
                q, r = divmod(n, 100)
                if q == 1:
                    _partial = "cento"
                else:
                    _partial = digits[q] + "cento"
                _partial += (
                    " " + _sub_thousand(r) if r else "")  # separa centinaia
                return _partial

        def _short_scale(n):
            if n >= max(SHORT_SCALE_IT.keys()):
                return "numero davvero enorme"
            n = int(n)
            assert 0 <= n
            res = []
            for i, z in enumerate(_split_by(n, 1000)):
                if not z:
                    continue
                number = _sub_thousand(z)
                if i:
                    number += ""  # separa ordini grandezza
                    number += hundreds[i]
                res.append(number)

            return ", ".join(reversed(res))

        def _split_by(n, split=1000):
            assert 0 <= n
            res = []
            while n:
                n, r = divmod(n, split)
                res.append(r)
            return res

        def _long_scale(n):
            if n >= max(LONG_SCALE_IT.keys()):
                return "numero davvero enorme"
            n = int(n)
            assert 0 <= n
            res = []
            for i, z in enumerate(_split_by(n, 1000000)):
                if not z:
                    continue
                number = pronounce_number_it(z, places, True, scientific)
                # strip off the comma after the thousand
                if i:
                    # plus one as we skip 'thousand'
                    # (and 'hundred', but this is excluded by index value)
                    number = number.replace(',', '')
                    number += " " + hundreds[i+1]
                res.append(number)
            return ", ".join(reversed(res))

        if short_scale:
            result += _short_scale(num)
        else:
            result += _long_scale(num)

    # normalizza unità misura singole e 'ragionevoli' ed ad inizio stringa
    if result == 'mila':
        result = 'mille'
    if result == 'milioni':
        result = 'un milione'
    if result == 'miliardi':
        result = 'un miliardo'
    if result[0:7] == 'unomila':
        result = result.replace('unomila', 'mille', 1)
    if result[0:10] == 'unomilioni':
        result = result.replace('unomilioni', 'un milione', 1)
    # if result[0:11] == 'unomiliardi':
    # result = result.replace('unomiliardi', 'un miliardo', 1)

    # Deal with fractional part
    if not num == int(num) and places > 0:
        result += " virgola"
        place = 10
        while int(num * place) % 10 > 0 and places > 0:
            result += " " + number_names[int(num * place) % 10]
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
                speak = "una"
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
            speak = pronounce_number_it(dt.hour)

        speak += " e"
        if dt.minute == 0:
            speak = speak[:-2]
            if not use_ampm:
                speak += " in punto"
        elif dt.minute == 15:
            speak += " un quarto"
        elif dt.minute == 45:
            speak += " tre quarti"
        else:
            if dt.minute < 10:
                speak += " zero"
            speak += " " + pronounce_number_it(dt.minute)

        if use_ampm:

            if dt.hour < 4:
                speak.strip()
            elif dt.hour > 20:
                speak += " della notte"
            elif dt.hour > 17:
                speak += " della sera"
            elif dt.hour > 12:
                speak += " del pomeriggio"
            else:
                speak += " della mattina"

        return speak
