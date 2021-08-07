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

from lingua_franca.lang.format_common import convert_to_mixed_fraction
from lingua_franca.lang.common_data_cs import _NUM_STRING_CS, \
    _FRACTION_STRING_CS, _LONG_SCALE_CS, _SHORT_SCALE_CS, _SHORT_ORDINAL_CS, _LONG_ORDINAL_CS


def nice_number_cs(number, speech=True, denominators=range(1, 21)):
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
    den_str = _FRACTION_STRING_CS[den]
    if whole == 0:
        if num == 1:
            return_string = '{}'.format(den_str)
        else:
            return_string = '{} {}'.format(num, den_str)
    elif num == 1:
        return_string = '{} a {}'.format(whole, den_str)
    else:
        return_string = '{} a {} {}'.format(whole, num, den_str)
    if num > 4:
        return_string = return_string[:-1]
    elif num > 1:
        return_string = return_string[:-1] + 'y'

    return return_string


def pronounce_number_cs(number, places=2, short_scale=True, scientific=False,
                        ordinals=False):
    """
    Convert a number to it's spoken equivalent

    For example, '5.2' would return 'five point two'

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
    num = number
    # deal with infinity
    if num == float("inf"):
        return "nekonečno"
    elif num == float("-inf"):
        return "záporné nekonečno"
    if scientific:
        number = '%E' % num
        n, power = number.replace("+", "").split("E")
        power = int(power)
        if power != 0:
            if ordinals:
                # This handles zápornés of powers separately from the normal
                # handling since each call disables the scientific flag
                return '{}{} krát deset k {}{} mocnině'.format(
                    'záporné ' if float(n) < 0 else '',
                    pronounce_number_cs(
                        abs(float(n)), places, short_scale, False, ordinals=False),
                    'záporné ' if power < 0 else '',
                    pronounce_number_cs(abs(power), places, short_scale, False, ordinals=True))
            else:
                # This handles zápornés of powers separately from the normal
                # handling since each call disables the scientific flag
                return '{}{} krát deset na mocninu {}{}'.format(
                    'záporné ' if float(n) < 0 else '',
                    pronounce_number_cs(
                        abs(float(n)), places, short_scale, False),
                    'záporné ' if power < 0 else '',
                    pronounce_number_cs(abs(power), places, short_scale, False))

    if short_scale:
        number_names = _NUM_STRING_CS.copy()
        number_names.update(_SHORT_SCALE_CS)
    else:
        number_names = _NUM_STRING_CS.copy()
        number_names.update(_LONG_SCALE_CS)

    digits = [number_names[n] for n in range(0, 20)]

    tens = [number_names[n] for n in range(10, 100, 10)]

    if short_scale:
        hundreds = [_SHORT_SCALE_CS[n] for n in _SHORT_SCALE_CS.keys()]
    else:
        hundreds = [_LONG_SCALE_CS[n] for n in _LONG_SCALE_CS.keys()]

    # deal with zápornés
    result = ""
    if num < 0:
        result = "záporné " if scientific else "mínus "
    num = abs(num)

    if not ordinals:
        try:
            # deal with 4 digits
            # usually if it's a 4 digit num it should be said like a date
            # i.e. 1972 => nineteen seventy two
            if len(str(num)) == 4 and isinstance(num, int):
                _num = str(num)
                # deal with 1000, 2000, 2001, 2100, 3123, etc
                # is skipped as the rest of the
                # functin deals with this already
                if _num[1:4] == '000' or _num[1:3] == '00' or int(_num[0:2]) >= 20:
                    pass
                # deal with 1900, 1300, etc
                # i.e. 1900 => nineteen hundred
                elif _num[2:4] == '00':
                    first = number_names[int(_num[0:2])]
                    last = number_names[100]
                    return first + " " + last
                # deal with 1960, 1961, etc
                # i.e. 1960 => nineteen sixty
                #      1961 => nineteen sixty one
                else:
                    first = number_names[int(_num[0:2])]
                    if _num[3:4] == '0':
                        last = number_names[int(_num[2:4])]
                    else:
                        second = number_names[int(_num[2:3])*10]
                        last = second + " " + number_names[int(_num[3:4])]
                    return first + " " + last
        # exception used to catch any unforseen edge cases
        # will default back to normal subroutine
        except Exception as e:
            # TODO this probably shouldn't go to stdout
            print('ERROR: Exception in pronounce_number_cs: {}' + repr(e))

    # check for a direct match
    if num in number_names and not ordinals:
        if num > 90:
            result += "jedna "
        result += number_names[num]
    else:
        def _sub_thousand(n, ordinals=False):
            assert 0 <= n <= 999
            if n in _SHORT_ORDINAL_CS and ordinals:
                return _SHORT_ORDINAL_CS[n]
            if n <= 19:
                return digits[n]
            elif n <= 99:
                q, r = divmod(n, 10)
                return tens[q - 1] + (" " + _sub_thousand(r, ordinals) if r
                                      else "")
            else:
                q, r = divmod(n, 100)
                return digits[q] + " sto" + (
                    " a " + _sub_thousand(r, ordinals) if r else "")

        def _short_scale(n):
            if n >= max(_SHORT_SCALE_CS.keys()):
                return "nekonečno"
            ordi = ordinals

            if int(n) != n:
                ordi = False
            n = int(n)
            assert 0 <= n
            res = []
            for i, z in enumerate(_split_by(n, 1000)):
                if not z:
                    continue
                number = _sub_thousand(z, not i and ordi)

                if i:
                    if i >= len(hundreds):
                        return ""
                    number += " "
                    if ordi:

                        if i * 1000 in _SHORT_ORDINAL_CS:
                            if z == 1:
                                number = _SHORT_ORDINAL_CS[i * 1000]
                            else:
                                number += _SHORT_ORDINAL_CS[i * 1000]
                        else:
                            if n not in _SHORT_SCALE_CS:
                                num = int("1" + "0" * (len(str(n)) - 2))

                                number += _SHORT_SCALE_CS[num] + "tý"
                            else:
                                number = _SHORT_SCALE_CS[n] + "tý"
                    else:
                        number += hundreds[i]
                res.append(number)
                ordi = False

            return ", ".join(reversed(res))

        def _split_by(n, split=1000):
            assert 0 <= n
            res = []
            while n:
                n, r = divmod(n, split)
                res.append(r)
            return res

        def _long_scale(n):
            if n >= max(_LONG_SCALE_CS.keys()):
                return "nekonečno"
            ordi = ordinals
            if int(n) != n:
                ordi = False
            n = int(n)
            assert 0 <= n
            res = []
            for i, z in enumerate(_split_by(n, 1000000)):
                if not z:
                    continue
                number = pronounce_number_cs(z, places, True, scientific,
                                             ordinals=ordi and not i)
                # strip off the comma after the thousand
                if i:
                    if i >= len(hundreds):
                        return ""
                    # plus one as we skip 'thousand'
                    # (and 'hundred', but this is excluded by index value)
                    number = number.replace(',', '')

                    if ordi:
                        if i * 1000000 in _LONG_ORDINAL_CS:
                            if z == 1:
                                number = _LONG_ORDINAL_CS[
                                    (i + 1) * 1000000]
                            else:
                                number += _LONG_ORDINAL_CS[
                                    (i + 1) * 1000000]
                        else:
                            if n not in _LONG_SCALE_CS:
                                num = int("1" + "0" * (len(str(n)) - 2))

                                number += " " + _LONG_SCALE_CS[
                                    num] + "tý"
                            else:
                                number = " " + _LONG_SCALE_CS[n] + "tý"
                    else:

                        number += " " + hundreds[i + 1]
                res.append(number)
            return ", ".join(reversed(res))

        if short_scale:
            result += _short_scale(num)
        else:
            result += _long_scale(num)

    # deal with scientific notation unpronounceable as number
    if not result and "e" in str(num):
        return pronounce_number_cs(num, places, short_scale, scientific=True)
    # Deal with fractional part
    elif not num == int(num) and places > 0:
        if abs(num) < 1.0 and (result == "mínus " or not result):
            result += "nula"
        result += " tečka"
        _num_str = str(num)
        _num_str = _num_str.split(".")[1][0:places]
        for char in _num_str:
            result += " " + number_names[int(char)]
    return result


def nice_time_cs(dt, speech=True, use_24hour=True, use_ampm=False):
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
            speak += pronounce_number_cs(int(string[0])) + " "
            speak += pronounce_number_cs(int(string[1]))
        else:
            speak = pronounce_number_cs(int(string[0:2]))

        speak += " "
        if string[3:5] == '00':
            speak += "sto"
        else:
            if string[3] == '0':
                speak += pronounce_number_cs(0) + " "
                speak += pronounce_number_cs(int(string[4]))
            else:
                speak += pronounce_number_cs(int(string[3:5]))
        return speak
    else:
        if dt.hour == 0 and dt.minute == 0:
            return "půlnoc"
        elif dt.hour == 12 and dt.minute == 0:
            return "poledne"

        hour = dt.hour % 12 or 12  # 12 hour clock and 0 is spoken as 12
        if dt.minute == 15:
            speak = "čtvrt po " + pronounce_number_cs(hour)
        elif dt.minute == 30:
            speak = "půl po " + pronounce_number_cs(hour)
        elif dt.minute == 45:
            next_hour = (dt.hour + 1) % 12 or 12
            speak = "třičtvrtě na " + pronounce_number_cs(next_hour)
        else:
            speak = pronounce_number_cs(hour)

            if dt.minute == 0:
                if not use_ampm:
                    return speak + " hodin"
            else:
                if dt.minute < 10:
                    speak += " oh"
                speak += " " + pronounce_number_cs(dt.minute)

        if use_ampm:
            if dt.hour > 11:
                speak += " p.m."
            else:
                speak += " a.m."

        return speak
