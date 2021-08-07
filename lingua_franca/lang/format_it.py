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

from lingua_franca.lang.format_common import convert_to_mixed_fraction
from lingua_franca.lang.common_data_it import _NUM_STRING_IT, \
    _FRACTION_STRING_IT, _LONG_SCALE_IT, _SHORT_SCALE_IT


def nice_number_it(number, speech=True, denominators=range(1, 21)):
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
    den_str = _FRACTION_STRING_IT[den]
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


def pronounce_number_it(number, places=2, short_scale=False, scientific=False):
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
    num = number
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
        number_names = _NUM_STRING_IT.copy()
        number_names.update(_SHORT_SCALE_IT)
    else:
        number_names = _NUM_STRING_IT.copy()
        number_names.update(_LONG_SCALE_IT)

    digits = [number_names[n] for n in range(0, 20)]

    tens = [number_names[n] for n in range(10, 100, 10)]

    if short_scale:
        hundreds = [_SHORT_SCALE_IT[n] for n in _SHORT_SCALE_IT.keys()]
    else:
        hundreds = [_LONG_SCALE_IT[n] for n in _LONG_SCALE_IT.keys()]

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
            if n >= max(_SHORT_SCALE_IT.keys()):
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
            if n >= max(_LONG_SCALE_IT.keys()):
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
        if abs(num) < 1.0 and (result == "meno " or not result):
            result += "zero"
        result += " virgola"
        _num_str = str(num)
        _num_str = _num_str.split(".")[1][0:places]
        for char in _num_str:
            result += " " + number_names[int(char)]
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
