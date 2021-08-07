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
from lingua_franca.lang.common_data_pt import _FRACTION_STRING_PT, \
    _NUM_STRING_PT


def nice_number_pt(number, speech, denominators=range(1, 21)):
    """ Portuguese helper for nice_number

    This function formats a float to human understandable functions. Like
    4.5 becomes "4 e meio" for speech and "4 1/2" for text

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
    # denominador
    den_str = _FRACTION_STRING_PT[den]
    # fracções
    if whole == 0:
        if num == 1:
            # um décimo
            return_string = 'um {}'.format(den_str)
        else:
            # três meio
            return_string = '{} {}'.format(num, den_str)
    # inteiros >10
    elif num == 1:
        # trinta e um
        return_string = '{} e {}'.format(whole, den_str)
    # inteiros >10 com fracções
    else:
        # vinte e 3 décimo
        return_string = '{} e {} {}'.format(whole, num, den_str)
    # plural
    if num > 1:
        return_string += 's'
    return return_string


def pronounce_number_pt(number, places=2):
    """
    Convert a number to it's spoken equivalent
     For example, '5.2' would return 'cinco virgula dois'
     Args:
        number(float or int): the number to pronounce (under 100)
        places(int): maximum decimal places to speak
    Returns:
        (str): The pronounced number
    """
    if abs(number) >= 100:
        # TODO: Support n > 100
        return str(number)

    result = ""
    if number < 0:
        result = "menos "
    number = abs(number)

    if number >= 20:
        tens = int(number - int(number) % 10)
        ones = int(number - tens)
        result += _NUM_STRING_PT[tens]
        if ones > 0:
            result += " e " + _NUM_STRING_PT[ones]
    else:
        result += _NUM_STRING_PT[int(number)]

    # Deal with decimal part, in portuguese is commonly used the comma
    # instead the dot. Decimal part can be written both with comma
    # and dot, but when pronounced, its pronounced "virgula"
    if not number == int(number) and places > 0:
        if abs(number) < 1.0 and (result == "menos " or not result):
            result += "zero"
        result += " vírgula"
        _num_str = str(number)
        _num_str = _num_str.split(".")[1][0:places]
        for char in _num_str:
            result += " " + _NUM_STRING_PT[int(char)]
    return result


def nice_time_pt(dt, speech=True, use_24hour=False, use_ampm=False):
    """
    Format a time to a comfortable human format
     For example, generate 'cinco treinta' for speech or '5:30' for
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
        # simply speak the number
        if dt.hour == 1:
            speak += "uma"
        else:
            speak += pronounce_number_pt(dt.hour)

        # equivalent to "quarter past ten"
        if dt.minute > 0:
            speak += " e " + pronounce_number_pt(dt.minute)

    else:
        # speak number and add daytime identifier
        # (equivalent to "in the morning")
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
            speak += "meia noite"
        elif hour == 12:
            speak += "meio dia"
        # 1 and 2 are pronounced in female form when talking about hours
        elif hour == 1 or hour == 13:
            speak += "uma"
        elif hour == 2 or hour == 14:
            speak += "duas"
        elif hour < 13:
            speak = pronounce_number_pt(hour)
        else:
            speak = pronounce_number_pt(hour - 12)

        if minute != 0:
            if minute == 15:
                speak += " e um quarto"
            elif minute == 30:
                speak += " e meia"
            elif minute == -15:
                speak += " menos um quarto"
            else:
                if minute > 0:
                    speak += " e " + pronounce_number_pt(minute)
                else:
                    speak += " " + pronounce_number_pt(minute)

        # exact time
        if minute == 0 and not use_ampm:
            # 3:00
            speak += " em ponto"

        if use_ampm:
            if hour > 0 and hour < 6:
                speak += " da madrugada"
            elif hour >= 6 and hour < 12:
                speak += " da manhã"
            elif hour >= 13 and hour < 21:
                speak += " da tarde"
            elif hour != 0 and hour != 12:
                speak += " da noite"
    return speak
