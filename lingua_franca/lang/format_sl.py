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

from lingua_franca.lang.common_data_sl import _NUM_STRING_SL, \
    _FRACTION_STRING_SL, _LONG_SCALE_SL, _SHORT_SCALE_SL, _SHORT_ORDINAL_SL
from lingua_franca.lang.format_common import convert_to_mixed_fraction


def nice_number_sl(number, speech=True, denominators=range(1, 21)):
    """ Slovenian helper for nice_number

    This function formats a float to human understandable functions. Like
    4.5 becomes "2 in polovica" for speech and "4 1/2" for text

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
    den_str = _FRACTION_STRING_SL[den]
    if whole == 0:
        return_string = '{} {}'.format(num, den_str)
    else:
        return_string = '{} in {} {}'.format(whole, num, den_str)

    if num % 100 == 1:
        pass
    elif num % 100 == 2:
        return_string = return_string[:-1] + 'i'
    elif num % 100 == 3 or num % 100 == 4:
        return_string = return_string[:-1] + 'e'
    else:
        return_string = return_string[:-1]

    return return_string


def pronounce_number_sl(num, places=2, short_scale=True, scientific=False,
                        ordinals=False):
    """
    Convert a number to it's spoken equivalent

    For example, '5.2' would return 'pet celih dve'

    Args:
        num(float or int): the number to pronounce (under 100)
        places(int): maximum decimal places to speak
        short_scale (bool) : use short (True) or long scale (False)
            https://en.wikipedia.org/wiki/Names_of_large_numbers
        scientific (bool): pronounce in scientific notation
        ordinals (bool): pronounce in ordinal form "first" instead of "one"
    Returns:
        (str): The pronounced number
    """
    # deal with infinity
    if num == float("inf"):
        return "neskončno"
    elif num == float("-inf"):
        return "minus neskončno"
    if scientific:
        number = '%E' % num
        n, power = number.replace("+", "").split("E")
        power = int(power)
        if power != 0:
            if ordinals:
                # This handles negatives of powers separately from the normal
                # handling since each call disables the scientific flag
                return '{}{} krat deset na {}{}'.format(
                    'minus ' if float(n) < 0 else '',
                    pronounce_number_sl(
                        abs(float(n)), places, short_scale, False, ordinals=False),
                    'minus ' if power < 0 else '',
                    pronounce_number_sl(abs(power), places, short_scale, False, ordinals=True))
            else:
                # This handles negatives of powers separately from the normal
                # handling since each call disables the scientific flag
                return '{}{} krat deset na {}{}'.format(
                    'minus ' if float(n) < 0 else '',
                    pronounce_number_sl(
                        abs(float(n)), places, short_scale, False),
                    'minus ' if power < 0 else '',
                    pronounce_number_sl(abs(power), places, short_scale, False))

    if short_scale:
        number_names = _NUM_STRING_SL.copy()
        number_names.update(_SHORT_SCALE_SL)
    else:
        number_names = _NUM_STRING_SL.copy()
        number_names.update(_LONG_SCALE_SL)

    digits = [number_names[n] for n in range(0, 20)]

    tens = [number_names[n] for n in range(10, 100, 10)]

    if short_scale:
        hundreds = [_SHORT_SCALE_SL[n] for n in _SHORT_SCALE_SL.keys()]
    else:
        hundreds = [_LONG_SCALE_SL[n] for n in _LONG_SCALE_SL.keys()]

    # deal with negatives
    result = ""
    if num < 0:
        result = "minus "
    num = abs(num)

    # check for a direct match
    if num in number_names and not ordinals:
        result += number_names[num]
    else:
        def _sub_thousand(n, ordinals=False, is_male=False):
            assert 0 <= n <= 999
            if n in _SHORT_ORDINAL_SL and ordinals:
                return _SHORT_ORDINAL_SL[n]
            if n <= 19:
                if is_male and n == 2:
                    return digits[n][:-1] + "a"
                return digits[n]
            elif n <= 99:
                q, r = divmod(n, 10)
                sub = _sub_thousand(r, False)
                if r == 2:
                    sub = sub[:-1] + "a"
                return ((sub + "in") if r else "") + (
                    tens[q - 1]) + ("i" if ordinals else "")
            else:
                q, r = divmod(n, 100)
                if q == 1:
                    qstr = ""
                else:
                    qstr = digits[q]
                return (qstr + "sto" + (
                    " " + _sub_thousand(r, ordinals) if r else ""))

        def _plural_hundreds(n, hundred, ordi=True):
            if hundred[-3:] != "jon":
                if ordi:
                    return hundred + "i"

                return hundred

            if n < 1000 or short_scale:
                if ordi:
                    return hundred + "ti"

                if n % 100 == 1:
                    return hundred
                elif n % 100 == 2:
                    return hundred + "a"
                elif n % 100 == 3 or n % 100 == 4:
                    return hundred + "i"
                else:
                    return hundred + "ov"
            else:
                n //= 1000

                if ordi:
                    return hundred[:-3] + "jardti"

                if n % 100 == 1:
                    return hundred[:-3] + "jarda"
                elif n % 100 == 2:
                    return hundred[:-3] + "jardi"
                elif n % 100 == 3 or n % 100 == 4:
                    return hundred[:-3] + "jarde"
                else:
                    return hundred[:-3] + "jard"

        def _short_scale(n):
            if n >= max(_SHORT_SCALE_SL.keys()):
                return "neskončno"
            ordi = ordinals

            if int(n) != n:
                ordi = False
            n = int(n)
            assert 0 <= n
            res = []

            split = _split_by(n, 1000)
            if ordinals and len([a for a in split if a > 0]) == 1:
                ordi_force = True
            else:
                ordi_force = False

            for i, z in enumerate(split):
                if not z:
                    continue

                if z == 1 and i == 1:
                    number = ""
                elif z > 100 and z % 100 == 2:
                    number = _sub_thousand(z, not i and ordi, is_male=True)
                elif z > 100 and z % 100 == 3:
                    number = _sub_thousand(z, not i and ordi) + "je"
                elif z > 1 or i == 0 or ordi:
                    number = _sub_thousand(z, not i and ordi)
                else:
                    number = ""

                if i:
                    if i >= len(hundreds):
                        return ""
                    if z > 1:
                        number += " "
                    number += _plural_hundreds(
                        z, hundreds[i], True if ordi_force else not i and ordi)
                res.append(number)
                ordi = False

            return " ".join(reversed(res))

        def _split_by(n, split=1000):
            assert 0 <= n
            res = []
            while n:
                n, r = divmod(n, split)
                res.append(r)
            return res

        def _long_scale(n):
            if n >= max(_LONG_SCALE_SL.keys()):
                return "neskončno"
            ordi = ordinals
            if int(n) != n:
                ordi = False
            n = int(n)
            assert 0 <= n
            res = []

            split = _split_by(n, 1000000)
            if ordinals and len([a for a in split if a > 0]) == 1:
                ordi_force = True
            else:
                ordi_force = False

            for i, z in enumerate(split):
                if not z:
                    continue

                number = pronounce_number_sl(z, places, True, scientific)
                if z > 100:
                    add = number.split()[0] + " "
                else:
                    add = ""
                if z % 100 == 2 and i >= 1:
                    number = add + digits[2][:-1] + "a"
                if z % 100 == 3 and i >= 1:
                    number = add + digits[3] + "je"

                # strip off the comma after the thousand
                if i:
                    if i >= len(hundreds):
                        return ""
                    # plus one as we skip 'thousand'
                    # (and 'hundred', but this is excluded by index value)
                    hundred = _plural_hundreds(
                        z, hundreds[i + 1], True if ordi_force else ordi and not i)

                    if z >= 1000:
                        z //= 1000
                        number = pronounce_number_sl(z, places, True, scientific,
                                                     ordinals=True if ordi_force else ordi and not i)

                    if z == 1:
                        number = hundred
                    else:
                        number += " " + hundred
                res.append(number)
            return " ".join(reversed(res))

        if short_scale:
            result += _short_scale(num)
        else:
            result += _long_scale(num)

    if ordinals:
        result = result.replace(" ", "")

    # deal with scientific notation unpronounceable as number
    if (not result or result == "neskončno") and "e" in str(num):
        return pronounce_number_sl(num, places, short_scale, scientific=True)
    # Deal with fractional part
    elif not num == int(num) and places > 0:
        if abs(num) < 1.0 and (result == "minus " or not result):
            result += "nič"

        if int(abs(num)) % 100 == 1:
            result += " cela"
        elif int(abs(num)) % 100 == 2:
            result += " celi"
        elif int(abs(num)) % 100 == 3 or int(abs(num)) % 100 == 4:
            result += " cele"
        else:
            result += " celih"

        _num_str = str(num)
        _num_str = _num_str.split(".")[1][0:places]
        for char in _num_str:
            result += " " + number_names[int(char)]
    return result


def nice_time_sl(dt, speech=True, use_24hour=False, use_ampm=False):
    """
    Format a time to a comfortable human format
    For example, generate 'pet trideset' for speech or '5:30' for
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

    def _hour_declension(hour):
        speak = pronounce_number_sl(hour)

        if hour == 1:
            return speak[:-1] + "ih"
        elif hour == 2 or hour == 4:
            return speak + "h"
        elif hour == 3:
            return speak[:-1] + "eh"
        elif hour == 7 or hour == 8:
            return speak[:-2] + "mih"
        else:
            return speak + "ih"

    # Generate a speakable version of the time
    if use_24hour:
        # "13 nič nič"
        speak = pronounce_number_sl(int(string[0:2]))

        speak += " "
        if string[3:5] == '00':
            speak += "nič nič"
        else:
            if string[3] == '0':
                speak += pronounce_number_sl(0) + " "
                speak += pronounce_number_sl(int(string[4]))
            else:
                speak += pronounce_number_sl(int(string[3:5]))
        return speak
    else:
        if dt.hour == 0 and dt.minute == 0:
            return "polnoč"
        elif dt.hour == 12 and dt.minute == 0:
            return "poldne"

        hour = dt.hour % 12 or 12  # 12 hour clock and 0 is spoken as 12
        if dt.minute == 0:
            speak = pronounce_number_sl(hour)
        elif dt.minute < 30:
            speak = pronounce_number_sl(
                dt.minute) + " čez " + pronounce_number_sl(hour)
        elif dt.minute == 30:
            next_hour = (dt.hour + 1) % 12 or 12
            speak = "pol " + _hour_declension(next_hour)
        elif dt.minute > 30:
            next_hour = (dt.hour + 1) % 12 or 12
            speak = pronounce_number_sl(
                60 - dt.minute) + " do " + _hour_declension(next_hour)

        if use_ampm:
            if dt.hour > 11:
                speak += " p.m."
            else:
                speak += " a.m."

        return speak
