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
"""
Format functions for castillian (es-es)

"""
from lingua_franca.lang.format_common import convert_to_mixed_fraction
from lingua_franca.lang.common_data_es import _NUM_STRING_ES, \
    _FRACTION_STRING_ES


def nice_number_es(number, speech=True, denominators=range(1, 21)):
    """ Spanish helper for nice_number

    This function formats a float to human understandable functions. Like
    4.5 becomes "4 y medio" for speech and "4 1/2" for text

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
        den_str = _FRACTION_STRING_ES[den]
        # if it is not an integer
        if whole == 0:
            # if there is no whole number
            if num == 1:
                # if numerator is 1, return "un medio", for example
                strNumber = 'un {}'.format(den_str)
            else:
                # else return "cuatro tercios", for example
                strNumber = '{} {}'.format(num, den_str)
        elif num == 1:
            # if there is a whole number and numerator is 1
            if den == 2:
                # if denominator is 2, return "1 y medio", for example
                strNumber = '{} y {}'.format(whole, den_str)
            else:
                # else return "1 y 1 tercio", for example
                strNumber = '{} y 1 {}'.format(whole, den_str)
        else:
            # else return "2 y 3 cuarto", for example
            strNumber = '{} y {} {}'.format(whole, num, den_str)
        if num > 1 and den != 3:
            # if the numerator is greater than 1 and the denominator
            # is not 3 ("tercio"), add an s for plural
            strNumber += 's'

    return strNumber


def pronounce_number_es(number, places=2):
    """
    Convert a number to it's spoken equivalent

    For example, '5.2' would return 'cinco coma dos'

    Args:
        num(float or int): the number to pronounce (under 100)
        places(int): maximum decimal places to speak
    Returns:
        (str): The pronounced number
    """
    if abs(number) >= 100:
        # TODO: Soporta a números por encima de 100
        return str(number)

    result = ""
    if number < 0:
        result = "menos "
    number = abs(number)

    # del 21 al 29 tienen una pronunciación especial
    if 20 <= number <= 29:
        tens = int(number-int(number) % 10)
        ones = int(number - tens)
        result += _NUM_STRING_ES[tens]
        if ones > 0:
            result = result[:-1]
            # a veinte le quitamos la "e" final para construir los
            # números del 21 - 29. Pero primero tenemos en cuenta
            # las excepciones: 22, 23 y 26, que llevan tilde.
            if ones == 2:
                result += "idós"
            elif ones == 3:
                result += "itrés"
            elif ones == 6:
                result += "iséis"
            else:
                result += "i" + _NUM_STRING_ES[ones]
    elif number >= 30:  # de 30 en adelante
        tens = int(number-int(number) % 10)
        ones = int(number - tens)
        result += _NUM_STRING_ES[tens]
        if ones > 0:
            result += " y " + _NUM_STRING_ES[ones]
    else:
        result += _NUM_STRING_ES[int(number)]

    # Deal with decimal part, in spanish is commonly used the comma
    # instead the dot. Decimal part can be written both with comma
    # and dot, but when pronounced, its pronounced "coma"
    if not number == int(number) and places > 0:
        if abs(number) < 1.0 and (result == "menos " or not result):
            result += "cero"
        result += " coma"
        _num_str = str(number)
        _num_str = _num_str.split(".")[1][0:places]
        for char in _num_str:
            result += " " + _NUM_STRING_ES[int(char)]
    return result


def nice_time_es(dt, speech=True, use_24hour=False, use_ampm=False):
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
        # Tenemos que tener en cuenta que cuando hablamos en formato
        # 24h, no hay que especificar ninguna precisión adicional
        # como "la noche", "la tarde" o "la mañana"
        # http://lema.rae.es/dpd/srv/search?id=YNoTWNJnAD6bhhVBf9
        if dt.hour == 1:
            speak += "la una"
        else:
            speak += "las " + pronounce_number_es(dt.hour)

        # las 14:04 son "las catorce cero cuatro"
        if dt.minute < 10:
            speak += " cero " + pronounce_number_es(dt.minute)
        else:
            speak += " " + pronounce_number_es(dt.minute)

    else:
        # Prepare for "tres menos cuarto" ??
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
            speak += "las doce"
        elif hour == 1 or hour == 13:
            speak += "la una"
        elif hour < 13:
            speak = "las " + pronounce_number_es(hour)
        else:
            speak = "las " + pronounce_number_es(hour-12)

        if minute != 0:
            # las horas especiales
            if minute == 15:
                speak += " y cuarto"
            elif minute == 30:
                speak += " y media"
            elif minute == -15:
                speak += " menos cuarto"
            else:  # seis y nueve. siete y veinticinco
                if minute > 0:
                    speak += " y " + pronounce_number_es(minute)
                else:  # si son las siete menos veinte, no ponemos la "y"
                    speak += " " + pronounce_number_es(minute)

        # si no especificamos de la tarde, noche, mañana, etc
        if minute == 0 and not use_ampm:
            # 3:00
            speak += " en punto"

        if use_ampm:
            # "de la noche" es desde que anochece hasta medianoche
            # así que decir que es desde las 21h es algo subjetivo
            # en España a las 20h se dice "de la tarde"
            # en castellano, las 12h es de la mañana o mediodía
            # así que diremos "de la tarde" a partir de las 13h.
            # http://lema.rae.es/dpd/srv/search?id=YNoTWNJnAD6bhhVBf9
            if hour >= 0 and hour < 6:
                speak += " de la madrugada"
            elif hour >= 6 and hour < 13:
                speak += " de la mañana"
            elif hour >= 13 and hour < 21:
                speak += " de la tarde"
            else:
                speak += " de la noche"
    return speak
