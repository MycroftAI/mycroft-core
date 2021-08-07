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
from lingua_franca.lang.common_data_ca import _FRACTION_STRING_CA, \
    _NUM_STRING_CA
from lingua_franca.internal import lookup_variant
from enum import IntEnum


class TimeVariantCA(IntEnum):
    DEFAULT = 0
    BELL = 1
    FULL_BELL = 2
    SPANISH_LIKE = 3


def nice_number_ca(number, speech, denominators=range(1, 21)):
    """ Catalan helper for nice_number

    This function formats a float to human understandable functions. Like
    4.5 becomes "4 i mig" for speech and "4 1/2" for text

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
    den_str = _FRACTION_STRING_CA[den]
    # fraccions
    if whole == 0:
        if num == 1:
            # un desè
            return_string = 'un {}'.format(den_str)
        else:
            # tres mig
            return_string = '{} {}'.format(num, den_str)
    # inteiros >10
    elif num == 1:
        # trenta-un
        return_string = '{}-{}'.format(whole, den_str)
    # inteiros >10 com fracções
    else:
        # vint i 3 desens
        return_string = '{} i {} {}'.format(whole, num, den_str)
    # plural
    if num > 1:
        return_string += 's'
    return return_string


def pronounce_number_ca(number, places=2):
    """
    Convert a number to it's spoken equivalent
     For example, '5.2' would return 'cinc coma dos'
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
        result = "menys "
    number = abs(number)

    if number >= 20:
        tens = int(number - int(number) % 10)
        ones = int(number - tens)
        result += _NUM_STRING_CA[tens]
        if ones > 0:
            if tens == 20:
                result += "-i-" + _NUM_STRING_CA[ones]
            else:
                result += "-" + _NUM_STRING_CA[ones]
    else:
        result += _NUM_STRING_CA[int(number)]

    # Deal with decimal part, in Catalan is commonly used the comma
    # instead the dot. Decimal part can be written both with comma
    # and dot, but when pronounced, its pronounced "coma"
    if not number == int(number) and places > 0:
        if abs(number) < 1.0 and (result == "menys " or not result):
            result += "zero"
        result += " coma"
        _num_str = str(number)
        _num_str = _num_str.split(".")[1][0:places]
        for char in _num_str:
            result += " " + _NUM_STRING_CA[int(char)]
    return result


@lookup_variant({
    "default": TimeVariantCA.DEFAULT,
    "traditional": TimeVariantCA.FULL_BELL,
    "bell": TimeVariantCA.BELL,
    "full_bell": TimeVariantCA.FULL_BELL,
    "spanish": TimeVariantCA.SPANISH_LIKE
})
def nice_time_ca(dt, speech=True, use_24hour=False, use_ampm=False,
                 variant=None):
    """
    Format a time to a comfortable human format
     For example, generate 'cinc trenta' for speech or '5:30' for
    text display.
     Args:
        dt (datetime): date to format (assumes already in local timezone)
        speech (bool): format for speech (default/True) or display (False)=Fal
        use_24hour (bool): output in 24-hour/military or 12-hour format
        use_ampm (bool): include the am/pm for 12-hour format
    Returns:
        (str): The formatted time string
    """
    variant = variant or TimeVariantCA.DEFAULT

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
    if variant == TimeVariantCA.BELL:
        # Bell Catalan Time System
        # https://en.wikipedia.org/wiki/Catalan_time_system

        if dt.minute < 7:
            next_hour = False
        elif dt.minute == 7 or dt.minute == 8:
            speak += "mig quart"
            next_hour = True
        elif dt.minute < 15:
            next_hour = False
        elif dt.minute == 15:
            speak += "un quart"
            next_hour = True
        elif dt.minute == 16:
            speak += "un quart i un minut"
            next_hour = True
        elif dt.minute < 21:
            speak += "un quart i " + pronounce_number_ca(
                dt.minute - 15) + " minuts"
            next_hour = True
        elif dt.minute == 22 or dt.minute == 23:
            speak += "un quart i mig"
            next_hour = True
        elif dt.minute < 30:
            speak += "un quart i " + pronounce_number_ca(
                dt.minute - 15) + " minuts"
            next_hour = True
        elif dt.minute == 30:
            speak += "dos quarts"
            next_hour = True
        elif dt.minute == 31:
            speak += "dos quarts i un minut"
            next_hour = True
        elif dt.minute < 37:
            speak += "dos quarts i " + pronounce_number_ca(
                dt.minute - 30) + " minuts"
            next_hour = True
        elif dt.minute == 37 or dt.minute == 38:
            speak += "dos quarts i mig"
            next_hour = True
        elif dt.minute < 45:
            speak += "dos quarts i " + pronounce_number_ca(
                dt.minute - 30) + " minuts"
            next_hour = True
        elif dt.minute == 45:
            speak += "tres quarts"
            next_hour = True
        elif dt.minute == 46:
            speak += "tres quarts i un minut"
            next_hour = True
        elif dt.minute < 52:
            speak += "tres quarts i " + pronounce_number_ca(
                dt.minute - 45) + " minuts"
            next_hour = True
        elif dt.minute == 52 or dt.minute == 53:
            speak += "tres quarts i mig"
            next_hour = True
        elif dt.minute > 53:
            speak += "tres quarts i " + pronounce_number_ca(
                dt.minute - 45) + " minuts"
            next_hour = True

        if next_hour == True:
            next_hour = (dt.hour + 1) % 12
            if next_hour == 0:
                speak += " de dotze"
                if dt.hour == 11:
                    speak += " del migdia"
                else:
                    speak += " de la nit"

            elif next_hour == 1:
                speak += " d'una"
                if dt.hour == 12:
                    speak += " de la tarda"
                else:
                    speak += " de la matinada"
            elif next_hour == 2:
                speak += "de dues"
                if dt.hour == 13:
                    speak += " de la tarda"
                else:
                    speak += " de la nit"

            elif next_hour == 11:
                speak += "d'onze"
                if dt.hour == 22:
                    speak += " de la nit"
                else:
                    speak += " del matí"
            else:
                speak += "de " + pronounce_number_ca(next_hour)
                if dt.hour == 0 and dt.hour < 5:
                    speak += " de la matinada"
                elif dt.hour >= 5 and dt.hour < 11:
                    speak += " del matí"
                elif dt.hour == 11:
                    speak += " del migdia"
                elif dt.hour >= 12 and dt.hour <= 17:
                    speak += " de la tarda"
                elif dt.hour >= 18 and dt.hour < 20:
                    speak += " del vespre"
                elif dt.hour >= 21 and dt.hour <= 23:
                    speak += " de la nit"


        else:
            hour = dt.hour % 12
            if hour == 0:
                speak += "les dotze"
            elif hour == 1:
                speak += "la una"
            elif hour == 2:
                speak += "les dues"
            else:
                speak += "les " + pronounce_number_ca(hour)

            if dt.minute == 0:
                speak += " en punt"
            elif dt.minute == 1:
                speak += " i un minut"
            else:
                speak += " i " + pronounce_number_ca(dt.minute) + " minuts"

            if dt.hour == 0:
                speak += " de la nit"
            elif dt.hour >= 1 and dt.hour < 6:
                speak += " de la matinada"
            elif dt.hour >= 6 and dt.hour < 11:
                speak += " del matí"
            elif dt.hour == 12:
                speak += " del migdia"
            elif dt.hour >= 13 and dt.hour < 19:
                speak += " de la tarda"
            elif dt.hour >= 19 and dt.hour < 21:
                speak += " del vespre"
            elif dt.hour >= 21 and dt.hour <= 23:
                speak += " de la nit"

    elif variant == TimeVariantCA.FULL_BELL:
        # Full Bell Catalan Time System
        # https://en.wikipedia.org/wiki/Catalan_time_system

        if dt.minute < 2:
            # en punt
            next_hour = False
        if dt.minute < 5:
            # tocades
            next_hour = False
        elif dt.minute < 7:
            # ben tocades
            next_hour = False
        elif dt.minute < 9:
            # mig quart
            speak += "mig quart"
            next_hour = True
        elif dt.minute < 12:
            # mig quart passat
            speak += "mig quart passat"
            next_hour = True
        elif dt.minute < 14:
            # mig quart passat
            speak += "mig quart ben passat"
            next_hour = True
        elif dt.minute < 17:
            speak += "un quart"
            next_hour = True
        elif dt.minute < 20:
            speak += "un quart tocat"
            next_hour = True
        elif dt.minute < 22:
            speak += "un quart ben tocat"
            next_hour = True
        elif dt.minute < 24:
            speak += "un quart i mig"
            next_hour = True
        elif dt.minute < 27:
            speak += "un quart i mig passat"
            next_hour = True
        elif dt.minute < 29:
            speak += "un quart i mig ben passat"
            next_hour = True
        elif dt.minute < 32:
            speak += "dos quarts"
            next_hour = True
        elif dt.minute < 35:
            speak += "dos quarts tocats"
            next_hour = True
        elif dt.minute < 37:
            speak += "dos quarts ben tocats"
            next_hour = True
        elif dt.minute < 39:
            speak += "dos quarts i mig"
            next_hour = True
        elif dt.minute < 42:
            speak += "dos quarts i mig passats"
            next_hour = True
        elif dt.minute < 44:
            speak += "dos quarts i mig ben passats"
            next_hour = True
        elif dt.minute < 47:
            speak += "tres quarts"
            next_hour = True
        elif dt.minute < 50:
            speak += "tres quarts tocats"
            next_hour = True
        elif dt.minute < 52:
            speak += "tres quarts ben tocats"
            next_hour = True
        elif dt.minute < 54:
            speak += "tres quarts i mig"
            next_hour = True
        elif dt.minute < 57:
            speak += "tres quarts i mig passats"
            next_hour = True
        elif dt.minute < 59:
            speak += "tres quarts i mig ben passats"
            next_hour = True
        elif dt.minute == 59:
            next_hour = False

        if next_hour == True:
            next_hour = (dt.hour + 1) % 12
            if next_hour == 0:
                speak += " de dotze"
                if dt.hour == 11:
                    speak += " del migdia"
                else:
                    speak += " de la nit"

            elif next_hour == 1:
                speak += " d'una"
                if dt.hour == 12:
                    speak += " de la tarda"
                else:
                    speak += " de la matinada"
            elif next_hour == 2:
                speak += "de dues"
                if dt.hour == 13:
                    speak += " de la tarda"
                else:
                    speak += " de la nit"

            elif next_hour == 11:
                speak += "d'onze"
                if dt.hour == 22:
                    speak += " de la nit"
                else:
                    speak += " del matí"
            else:
                speak += "de " + pronounce_number_ca(next_hour)
                if dt.hour == 0 and dt.hour < 5:
                    speak += " de la matinada"
                elif dt.hour >= 5 and dt.hour < 11:
                    speak += " del matí"
                elif dt.hour == 11:
                    speak += " del migdia"
                elif dt.hour >= 12 and dt.hour <= 17:
                    speak += " de la tarda"
                elif dt.hour >= 18 and dt.hour < 20:
                    speak += " del vespre"
                elif dt.hour >= 21 and dt.hour <= 23:
                    speak += " de la nit"

        else:
            hour = dt.hour % 12
            if dt.minute == 59:
                hour = (hour + 1) % 12
            if hour == 0:
                speak += "les dotze"
            elif hour == 1:
                speak += "la una"
            elif hour == 2:
                speak += "les dues"
            else:
                speak += "les " + pronounce_number_ca(hour)

            if dt.minute == 0:
                speak += " en punt"
            elif dt.minute > 1 and dt.minute < 5:
                if hour == 1:
                    speak += " tocada"
                else:
                    speak += " tocades"
            elif dt.minute < 7:
                if hour == 1:
                    speak += " ben tocada"
                else:
                    speak += " ben tocades"

            if dt.hour == 0:
                if hour == 1:
                    speak += " de la matinada"
                else:
                    speak += " de la nit"
            elif dt.hour < 6:
                if hour == 6:
                    speak += " del matí"
                else:
                    speak += " de la matinada"
            elif dt.hour < 12:
                if hour == 12:
                    speak += " del migdia"
                else:
                    speak += " del matí"
            elif dt.hour == 12:
                if hour == 1:
                    speak += " de la tarda"
                else:
                    speak += " del migdia"
            elif dt.hour < 19:
                if hour == 7:
                    speak += " del vespre"
                else:
                    speak += " de la tarda"
            elif dt.hour < 21:
                if hour == 9:
                    speak += " de la nit"
                else:
                    speak += " del vespre"
            elif dt.hour <= 23:
                speak += " de la nit"

    elif variant == TimeVariantCA.SPANISH_LIKE:
        # Prepare for "tres menys quart" ??
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

        if hour == 0 or hour == 12:
            speak += "les dotze"
        elif hour == 1 or hour == 13:
            speak += "la una"
        elif hour < 13:
            speak = "les " + pronounce_number_ca(hour)
        else:
            speak = "les " + pronounce_number_ca(hour - 12)

        if minute != 0:
            # les hores especials
            if minute == 15:
                speak += " i quart"
            elif minute == 30:
                speak += " i mitja"
            elif minute == -15:
                speak += " menys quart"
            else:  # sis i nou. set i veint-i-cinc
                if minute > 0:
                    speak += " i " + pronounce_number_ca(minute)
                else:  # si son las set menys vint, no posem la "i"
                    speak += " " + pronounce_number_ca(minute)

    # Default Watch Time Sytem
    else:
        if use_24hour:
            # simply speak the number
            if dt.hour == 1:
                speak += "la una"
            elif dt.hour == 2:
                speak += "les dues"
            elif dt.hour == 21:
                speak += "les vint-i-una"
            elif dt.hour == 22:
                speak += "les vint-i-dues"
            else:
                speak += "les " + pronounce_number_ca(dt.hour)

            if dt.minute > 0:
                speak += " i " + pronounce_number_ca(dt.minute)

        else:
            # speak number and add daytime identifier
            # (equivalent to "in the morning")
            if dt.hour == 0:
                speak += "les dotze"
            # 1 and 2 are pronounced in female form when talking about hours
            elif dt.hour == 1 or dt.hour == 13:
                speak += "la una"
            elif dt.hour == 2 or dt.hour == 14:
                speak += "les dues"
            elif dt.hour < 13:
                speak = "les " + pronounce_number_ca(dt.hour)
            else:
                speak = "les " + pronounce_number_ca(dt.hour - 12)

            # exact time
            if dt.minute == 0:
                # 3:00
                speak += " en punt"
            # else
            else:
                speak += " i " + pronounce_number_ca(dt.minute)

            # TODO: review day-periods
            if use_ampm:
                if dt.hour == 0:
                    speak += " de la nit"
                elif dt.hour >= 1 and dt.hour < 6:
                    speak += " de la matinada"
                elif dt.hour >= 6 and dt.hour < 12:
                    speak += " del matí"
                elif dt.hour == 12:
                    speak += " del migdia"
                elif dt.hour >= 13 and dt.hour <= 18:
                    speak += " de la tarda"
                elif dt.hour >= 19 and dt.hour < 21:
                    speak += " del vespre"
                elif dt.hour != 0 and dt.hour != 12:
                    speak += " de la nit"
    return speak
