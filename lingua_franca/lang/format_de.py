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
from lingua_franca.lang.common_data_de import _EXTRA_SPACE_DE, \
    _FRACTION_STRING_DE, _MONTHS_DE, _NUM_POWERS_OF_TEN_DE, _NUM_STRING_DE
from math import floor


def nice_number_de(number, speech=True, denominators=range(1, 21)):
    """ German helper for nice_number
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
    den_str = _FRACTION_STRING_DE[den]
    if whole == 0:
        if num == 1:
            return_string = 'ein {}'.format(den_str)
        else:
            return_string = '{} {}'.format(num, den_str)
    elif num == 1:
        return_string = '{} und ein {}'.format(whole, den_str)
    else:
        return_string = '{} und {} {}'.format(whole, num, den_str)

    return return_string


def pronounce_number_de(number, places=2, short_scale=True, scientific=False,
                        ordinals=False):
    """
    Convert a number to it's spoken equivalent

    For example, '5.2' would return 'five point two'

    Args:
        number(float or int): the number to pronounce (under 100)
        places(int): maximum decimal places to speak
        short_scale (bool) : use short (True) or long scale (False)
            https://en.wikipedia.org/wiki/Names_of_large_numbers
        scientific (bool): pronounce in scientific notation
        ordinals (bool): pronounce in ordinal form "first" instead of "one"
    Returns:
        (str): The pronounced number
    """

    # TODO short_scale, scientific and ordinals
    # currently ignored

    def pronounce_triplet_de(num):
        result = ""
        num = floor(num)
        if num > 99:
            hundreds = floor(num / 100)
            if hundreds > 0:
                result += _NUM_STRING_DE[
                    hundreds] + _EXTRA_SPACE_DE + 'hundert' + _EXTRA_SPACE_DE
                num -= hundreds * 100
        if num == 0:
            result += ''  # do nothing
        elif num == 1:
            result += 'eins'  # need the s for the last digit
        elif num <= 20:
            result += _NUM_STRING_DE[num]  # + _EXTRA_SPACE_DA
        elif num > 20:
            ones = num % 10
            tens = num - ones
            if ones > 0:
                result += _NUM_STRING_DE[ones] + _EXTRA_SPACE_DE
                if tens > 0:
                    result += 'und' + _EXTRA_SPACE_DE
            if tens > 0:
                result += _NUM_STRING_DE[tens] + _EXTRA_SPACE_DE
        return result

    def pronounce_fractional_de(num,
                                places):  # fixed number of places even with
        # trailing zeros
        result = ""
        place = 10
        while places > 0:  # doesn't work with 1.0001 and places = 2: int(
            # number*place) % 10 > 0 and places > 0:
            result += " " + _NUM_STRING_DE[int(num * place) % 10]
            if int(num * place) % 10 == 1:
                result += 's'  # "1" is pronounced "eins" after the decimal
                # point
            place *= 10
            places -= 1
        return result

    def pronounce_whole_number_de(num, scale_level=0):
        if num == 0:
            return ''

        num = floor(num)
        result = ''
        last_triplet = num % 1000

        if last_triplet == 1:
            if scale_level == 0:
                if result != '':
                    result += '' + 'eins'
                else:
                    result += "eins"
            elif scale_level == 1:
                result += 'ein' + _EXTRA_SPACE_DE + 'tausend' + _EXTRA_SPACE_DE
            else:
                result += "eine " + _NUM_POWERS_OF_TEN_DE[scale_level] + ' '
        elif last_triplet > 1:
            result += pronounce_triplet_de(last_triplet)
            if scale_level == 1:
                # result += _EXTRA_SPACE_DA
                result += 'tausend' + _EXTRA_SPACE_DE
            if scale_level >= 2:
                # if _EXTRA_SPACE_DA == '':
                #    result += " "
                result += " " + _NUM_POWERS_OF_TEN_DE[scale_level]
            if scale_level >= 2:
                if scale_level % 2 == 0:
                    result += "e"  # MillionE
                result += "n "  # MilliardeN, MillioneN

        num = floor(num / 1000)
        scale_level += 1
        return pronounce_whole_number_de(num,
                                         scale_level) + result  # + _EXTRA_SPACE_DA

    result = ""
    if abs(number) >= 1000000000000000000000000:  # cannot do more than this
        return str(number)
    elif number == 0:
        return str(_NUM_STRING_DE[0])
    elif number < 0:
        return "minus " + pronounce_number_de(abs(number), places)
    else:
        if number == int(number):
            return pronounce_whole_number_de(number)
        else:
            whole_number_part = floor(number)
            fractional_part = number - whole_number_part
            result += pronounce_whole_number_de(whole_number_part)
            if places > 0:
                result += " Komma"
                result += pronounce_fractional_de(fractional_part, places)
            return result


def pronounce_ordinal_de(number):
    """
      This function pronounces a number as an ordinal

      1 -> first
      2 -> second

      Args:
          number (int): the number to format
      Returns:
          (str): The pronounced number string.
      """
    # ordinals for 1, 3, 7 and 8 are irregular
    # this produces the base form, it will have to be adapted for genus,
    # casus, numerus

    ordinals = ["nullte", "erste", "zweite", "dritte", "vierte", "fünfte",
                "sechste", "siebte", "achte"]

    # only for whole positive numbers including zero
    if number < 0 or number != int(number):
        return number
    elif number < 9:
        return ordinals[number]
    elif number < 20:
        return pronounce_number_de(number) + "te"
    else:
        return pronounce_number_de(number) + "ste"


def nice_time_de(dt, speech=True, use_24hour=False, use_ampm=False):
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
    if not speech:
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
        return string

    # Generate a speakable version of the time
    speak = ""
    if use_24hour:
        if dt.hour == 1:
            speak += "ein"  # 01:00 is "ein Uhr" not "eins Uhr"
        else:
            speak += pronounce_number_de(dt.hour)
        speak += " Uhr"
        if not dt.minute == 0:  # zero minutes are not pronounced, 13:00 is
            # "13 Uhr" not "13 hundred hours"
            speak += " " + pronounce_number_de(dt.minute)

        return speak  # ampm is ignored when use_24hour is true
    else:
        if dt.hour == 0 and dt.minute == 0:
            return "Mitternacht"
        elif dt.hour == 12 and dt.minute == 0:
            return "Mittag"
        elif dt.minute == 15:
            # sentence relative to next hour and 0 spoken as 12
            next_hour = (dt.hour + 1) % 12 or 12
            speak = "viertel " + pronounce_number_de(next_hour)
        elif dt.minute == 30:
            next_hour = (dt.hour + 1) % 12 or 12
            speak = "halb " + pronounce_number_de(next_hour)
        elif dt.minute == 45:
            next_hour = (dt.hour + 1) % 12 or 12
            speak = "dreiviertel " + pronounce_number_de(next_hour)
        else:
            hour = dt.hour % 12 or 12  # 12 hour clock and 0 is spoken as 12
            if hour == 1:  # 01:00 and 13:00 is "ein Uhr" not "eins Uhr"
                speak += 'ein'
            else:
                speak += pronounce_number_de(hour)
            speak += " Uhr"

            if not dt.minute == 0:
                speak += " " + pronounce_number_de(dt.minute)

        if use_ampm:
            if 3 <= dt.hour < 12:
                speak += " morgens"  # 03:00 - 11:59 morgens/in the morning
            elif 12 <= dt.hour < 18:
                speak += " nachmittags"  # 12:01 - 17:59 nachmittags/afternoon
            elif 18 <= dt.hour < 22:
                speak += " abends"  # 18:00 - 21:59 abends/evening
            else:
                speak += " nachts"  # 22:00 - 02:59 nachts/at night

        return speak


def nice_response_de(text):
    # check for months and call _nice_ordinal_de declension of ordinals
    # replace "^" with "hoch" (to the power of)
    words = text.split()

    for idx, word in enumerate(words):
        if word.lower() in _MONTHS_DE:
            text = _nice_ordinal_de(text)

        if word == '^':
            wordNext = words[idx + 1] if idx + 1 < len(words) else ""
            if wordNext.isnumeric():
                words[idx] = "hoch"
                text = " ".join(words)
    return text


def _nice_ordinal_de(text, speech=True):
    # check for months for declension of ordinals before months
    # depending on articles/prepositions
    normalized_text = text
    words = text.split()

    for idx, word in enumerate(words):
        wordNext = words[idx + 1] if idx + 1 < len(words) else ""
        wordPrev = words[idx - 1] if idx > 0 else ""
        if word[-1:] == ".":
            if word[:-1].isdecimal():
                if wordNext.lower() in _MONTHS_DE:
                    word = pronounce_ordinal_de(int(word[:-1]))
                    if wordPrev.lower() in ["am", "dem", "vom", "zum",
                                            "(vom", "(am", "zum"]:
                        word += "n"
                    elif wordPrev.lower() not in ["der", "die", "das"]:
                        word += "r"
                    words[idx] = word
            normalized_text = " ".join(words)
    return normalized_text
