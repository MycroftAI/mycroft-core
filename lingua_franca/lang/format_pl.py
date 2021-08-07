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
from lingua_franca.lang.common_data_pl import _NUM_STRING_PL, \
    _FRACTION_STRING_PL, _SHORT_SCALE_PL, _SHORT_ORDINAL_PL, _ALT_ORDINALS_PL
from lingua_franca.internal import FunctionNotLocalizedError


def nice_number_pl(number, speech=True, denominators=range(1, 21)):
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
    den_str = _FRACTION_STRING_PL[den]
    if whole == 0:
        return_string = '{} {}'.format(num, den_str)
    else:
        return_string = '{} i {} {}'.format(whole, num, den_str)
    if num > 1:
        return_string = return_string[:-1] + 'e'
    return return_string


def pronounce_number_pl(num, places=2, short_scale=True, scientific=False,
                        ordinals=False, scientific_run=False):
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
    # deal with infinity
    if num == float("inf"):
        return "nieskończoność"
    elif num == float("-inf"):
        return "minus nieskończoność"
    if scientific:
        number = '%E' % num
        n, power = number.replace("+", "").split("E")
        power = int(power)
        if power != 0:
            if ordinals:
                # This handles negatives of powers separately from the normal
                # handling since each call disables the scientific flag
                return '{}{} razy dziesięć do {}{} potęgi'.format(
                    'minus ' if float(n) < 0 else '',
                    pronounce_number_pl(
                        abs(float(n)), places, short_scale, False, ordinals=False, scientific_run=True),
                    'minus ' if power < 0 else '',
                    pronounce_number_pl(abs(power), places, short_scale, False, ordinals=True, scientific_run=True))
            else:
                # This handles negatives of powers separately from the normal
                # handling since each call disables the scientific flag
                return '{}{} razy dziesięć do potęgi {}{}'.format(
                    'minus ' if float(n) < 0 else '',
                    pronounce_number_pl(
                        abs(float(n)), places, short_scale, False),
                    'minus ' if power < 0 else '',
                    pronounce_number_pl(abs(power), places, short_scale, False))

    number_names = _NUM_STRING_PL.copy()
    number_names.update(_SHORT_SCALE_PL)

    digits = [number_names[n] for n in range(0, 20)]
    if ordinals:
        tens = [_SHORT_ORDINAL_PL[n] for n in range(10, 100, 10)]
    else:
        tens = [number_names[n] for n in range(10, 100, 10)]
    hundreds = [_SHORT_SCALE_PL[n] for n in _SHORT_SCALE_PL.keys()]

    # deal with negatives
    result = ""
    if num < 0:
        result = "minus "
    num = abs(num)

    # check for a direct match
    if num in number_names and not ordinals:
        result += number_names[num]
    else:
        def _sub_thousand(n, ordinals=False, iteration=0):
            assert 0 <= n <= 999

            _, n_mod = divmod(n, 10)
            if iteration > 0 and n in _ALT_ORDINALS_PL and ordinals:
                return _ALT_ORDINALS_PL[n]
            elif n in _SHORT_ORDINAL_PL and ordinals:
                return _SHORT_ORDINAL_PL[n] if not scientific_run \
                    else _ALT_ORDINALS_PL[n]
            if n <= 19:
                return digits[n] if not scientific_run or not ordinals\
                    else digits[n][:-1] + "ej"
            elif n <= 99:
                q, r = divmod(n, 10)
                tens_text = tens[q - 1]
                if scientific_run:
                    tens_text = tens_text[:-1] + "ej"
                return tens_text + (" " + _sub_thousand(r, ordinals) if r
                                    else "")
            else:
                q, r = divmod(n, 100)
                digit_name = digits[q]
                if q*100 in _NUM_STRING_PL:
                    digit_name = _NUM_STRING_PL[q*100]

                return digit_name + (
                    " " + _sub_thousand(r, ordinals) if r else "")

        def _short_scale(n):
            if n >= max(_SHORT_SCALE_PL.keys()):
                return "nieskończoność"
            ordi = ordinals

            if int(n) != n:
                ordi = False
            n = int(n)
            assert 0 <= n
            res = []
            for i, z in enumerate(_split_by(n, 1000)):
                if not z:
                    continue
                number = _sub_thousand(z, ordi, iteration=i)

                if i:
                    if i >= len(hundreds):
                        return ""
                    number += " "
                    if ordi:
                        if i * 1000 in _SHORT_ORDINAL_PL:
                            if z == 1:
                                number = _SHORT_ORDINAL_PL[i * 1000]
                            else:
                                number += _SHORT_ORDINAL_PL[i * 1000]
                        else:
                            if n not in _SHORT_SCALE_PL:
                                num = int("1" + "0" * (len(str(n)) - 2))

                                number += _SHORT_SCALE_PL[num] + "owa"
                            else:
                                number = _SHORT_SCALE_PL[n] + "ty"
                    else:
                        hundreds_text = _SHORT_SCALE_PL[float(pow(1000, i))]
                        if z != 1:
                            _, z_mod = divmod(z, 10)
                            _, z_mod_tens = divmod(z, 100)
                            n_main, _ = divmod(z_mod_tens, 10)
                            if i == 1:
                                if n_main != 1 and 5 > z_mod > 0:
                                    hundreds_text += "e"
                                else:
                                    hundreds_text = "tysięcy"
                            elif i > 1:
                                hundreds_text += "y" if 5 > z_mod > 0 else "ów"

                        number += hundreds_text
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

        result += _short_scale(num)

    # deal with scientific notation unpronounceable as number
    if not result and "e" in str(num):
        return pronounce_number_pl(num, places, short_scale, scientific=True)
    # Deal with fractional part
    elif not num == int(num) and places > 0:
        if abs(num) < 1.0 and (result == "minus " or not result):
            result += "zero"
        result += " przecinek"
        _num_str = str(num)
        _num_str = _num_str.split(".")[1][0:places]
        for char in _num_str:
            result += " " + number_names[int(char)]
    return result


def nice_time_pl(dt, speech=True, use_24hour=True, use_ampm=False):
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
    string = dt.strftime("%H:%M")
    if not speech:
        return string

    # Generate a speakable version of the time
    speak = ""

    # Either "0 8 hundred" or "13 hundred"
    if string[0:2] == '00':
        speak = ""
    elif string[0] == '0':
        speak += pronounce_number_pl(int(string[1]), ordinals=True)
        speak = speak[:-1] + 'a'
    else:
        speak = pronounce_number_pl(int(string[0:2]), ordinals=True)
        speak = speak[:-1] + 'a'

    speak += ' ' if string[0:2] != '00' else ''
    if string[3:5] == '00':
        speak += 'zero zero'
    else:
        if string[3] == '0':
            speak += pronounce_number_pl(int(string[4]))
        else:
            speak += pronounce_number_pl(int(string[3:5]))

    if string[0:2] == '00':
        speak += " po północy"
    return speak


def nice_duration_pl(duration, speech=True):
    """ Convert duration to a nice spoken timespan

    Args:
        seconds: number of seconds
        minutes: number of minutes
        hours: number of hours
        days: number of days
    Returns:
        str: timespan as a string
    """

    # TODO this is a kludge around the fact that only Polish has a
    # localized nice_duration()
    if not speech:
        raise FunctionNotLocalizedError

    days = int(duration // 86400)
    hours = int(duration // 3600 % 24)
    minutes = int(duration // 60 % 60)
    seconds = int(duration % 60)

    out = ''
    sec_main, sec_div = divmod(seconds, 10)
    min_main, min_div = divmod(minutes, 10)
    hour_main, hour_div = divmod(hours, 10)

    if days > 0:
        out += pronounce_number_pl(days) + " "
        if days == 1:
            out += 'dzień'
        else:
            out += 'dni'
    if hours > 0:
        if out:
            out += " "
        out += get_pronounce_number_for_duration(hours) + " "
        if hours == 1:
            out += 'godzina'
        elif hour_main == 1 or hour_div > 4:
            out += 'godzin'
        else:
            out += 'godziny'
    if minutes > 0:
        if out:
            out += " "
        out += get_pronounce_number_for_duration(minutes) + " "
        if minutes == 1:
            out += 'minuta'
        elif min_main == 1 or min_div > 4:
            out += 'minut'
        else:
            out += 'minuty'
    if seconds > 0:
        if out:
            out += " "
        out += get_pronounce_number_for_duration(seconds) + " "
        if sec_div == 0:
            out += 'sekund'
        elif seconds == 1:
            out += 'sekunda'
        elif sec_main == 1 or sec_div > 4:
            out += 'sekund'
        else:
            out += 'sekundy'

    return out


def get_pronounce_number_for_duration(num):
    pronounced = pronounce_number_pl(num)

    return 'jedna' if pronounced == 'jeden' else pronounced
