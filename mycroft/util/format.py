# -*- coding: iso-8859-15 -*-
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
FRACTION_STRING_EN = {
    2: 'half',
    3: 'third',
    4: 'forth',
    5: 'fifth',
    6: 'sixth',
    7: 'seventh',
    8: 'eigth',
    9: 'ninth',
    10: 'tenth',
    11: 'eleventh',
    12: 'twelveth',
    13: 'thirteenth',
    14: 'fourteenth',
    15: 'fifteenth',
    16: 'sixteenth',
    17: 'seventeenth',
    18: 'eighteenth',
    19: 'nineteenth',
    20: 'twentyith'
}

FRACTION_STRING_PT = {
    2: 'meio',
    3: u'terço',
    4: 'quarto',
    5: 'quinto',
    6: 'sexto',
    7: u'sétimo',
    8: 'oitavo',
    9: 'nono',
    10: u'décimo',
    11: 'onze avos',
    12: 'doze avos',
    13: 'treze avos',
    14: 'catorze avos',
    15: 'quinze avos',
    16: 'dezasseis avos',
    17: 'dezassete avos',
    18: 'dezoito avos',
    19: 'dezanove avos',
    20: u'vigésimo',
    30: u'trigésimo',
    100: u'centésimo',
    1000: u'milésimo'
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

def nice_number(number, lang="en-us", speech=True, denominators=None):
    """Format a float to human readable functions

    This function formats a float to human understandable functions. Like
    4.5 becomes 4 and a half for speech and 4 1/2 for text
    Args:
        number (str): the float to format
        lang (str): the code for the language text is in
        speech (bool): to return speech representation or text representation
        denominators (iter of ints): denominators to use, default [1 .. 20]
    Returns:
        (str): The formatted string.
    """
    result = convert_number(number, denominators)
    if not result:
        return str(round(number, 3))

    if not speech:
        whole, num, den = result
        if num == 0:
            return str(whole)
        else:
            return '{} {}/{}'.format(whole, num, den)

    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return nice_number_en(result)
    elif lang_lower.startswith("pt"):
        return nice_number_pt(result)
    elif lang_lower.startswith("it"):
        return nice_number_it(result)
    # TODO: Normalization for other languages
    return str(number)


def nice_number_en(result):
    """ English conversion for nice_number """
    whole, num, den = result
    if num == 0:
        return str(whole)
    den_str = FRACTION_STRING_EN[den]
    if whole == 0:
        if num == 1:
            return_string = 'a {}'.format(den_str)
        else:
            return_string = '{} {}'.format(num, den_str)
    elif num == 1:
        return_string = '{} and a {}'.format(whole, den_str)
    else:
        return_string = '{} and {} {}'.format(whole, num, den_str)
    if num > 1:
        return_string += 's'
    return return_string


def nice_number_pt(result):
    """ Portuguese conversion for nice_number """
    whole, num, den = result
    if num == 0:
        return str(whole)
    # denominador
    den_str = FRACTION_STRING_PT[den]
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


def nice_number_it(result):
    """ Italian conversion for nice_number """
    whole, num, den = result
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

    # plurali
    if num > 1:
        return_string += 'i'
    else:
        return_string += 'o'

    return return_string


def convert_number(number, denominators):
    """ Convert floats to mixed fractions """
    int_number = int(number)
    if int_number == number:
        return int_number, 0, 1

    frac_number = abs(number - int_number)
    if not denominators:
        denominators = range(1, 21)

    for denominator in denominators:
        numerator = abs(frac_number) * denominator
        if (abs(numerator - round(numerator)) < 0.01):
            break
    else:
        return None

    return int_number, int(round(numerator)), denominator
