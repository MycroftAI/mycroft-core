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

from mycroft.util.lang.format_en import *
from mycroft.util.lang.format_pt import *
from mycroft.util.lang.format_it import *


def nice_number(number, lang="en-us", speech=True, denominators=None):
    """Format a float to human readable functions

    This function formats a float to human understandable functions. Like
    4.5 becomes 4 and a half for speech and 4 1/2 for text
    Args:
        number (int or float): the float to format
        lang (str): code for the language to use
        speech (bool): format for speech (True) or display (False)
        denominators (iter of ints): denominators to use, default [1 .. 20]
    Returns:
        (str): The formatted string.
    """
    result = _convert_to_mixed_fraction(number, denominators)
    if not result:
        # Give up, just represent as a 3 decimal number
        return str(round(number, 3))

    if not speech:
        whole, num, den = result
        if num == 0:
            # TODO: Number grouping?  E.g. "1,000,000"
            return str(whole)
        else:
            return '{} {}/{}'.format(whole, num, den)

    # Convert to spoken representation in appropriate language
    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return nice_number_en(result)
    elif lang_lower.startswith("pt"):
        return nice_number_pt(result)

    # Default to the raw number for unsupported languages,
    # hopefully the STT engine will pronounce understandably.
    return str(number)


def nice_time(dt, lang="en-us", speech=True, use_24hour=False,
              use_ampm=False):
    """
    Format a time to a comfortable human format

    For example, generate 'five thirty' for speech or '5:30' for
    text display.

    Args:
        dt (datetime): date to format (assumes already in local timezone)
        lang (str): code for the language to use
        speech (bool): format for speech (default/True) or display (False)=Fal
        use_24hour (bool): output in 24-hour/military or 12-hour format
        use_ampm (bool): include the am/pm for 12-hour format
    Returns:
        (str): The formatted time string
    """
    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return nice_time_en(dt, speech, use_24hour, use_ampm)
    # TODO: Other languages
    return str(dt)


def pronounce_number(number, lang="en-us", places=2):
    """
    Convert a number to it's spoken equivalent

    For example, '5' would be 'five'

    Args:
        number: the number to pronounce
    Returns:
        (str): The pronounced number
    """
    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return pronounce_number_en(number, places=places)

    # Default to just returning the numeric value
    return str(number)


def _convert_to_mixed_fraction(number, denominators):
    """
    Convert floats to components of a mixed fraction representation

    Returns the closest fractional representation using the
    provided denominators.  For example, 4.500002 would become
    the whole number 4, the numerator 1 and the denominator 2

    Args:
        number (float): number for convert
        denominators (iter of ints): denominators to use, default [1 .. 20]
    Returns:
        whole, numerator, denominator (int): Integers of the mixed fraction
    """
    int_number = int(number)
    if int_number == number:
        return int_number, 0, 1  # whole number, no fraction

    frac_number = abs(number - int_number)
    if not denominators:
        denominators = range(1, 21)

    for denominator in denominators:
        numerator = abs(frac_number) * denominator
        if (abs(numerator - round(numerator)) < 0.01):  # 0.01 accuracy
            break
    else:
        return None

    return int_number, int(round(numerator)), denominator
