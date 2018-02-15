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
from mycroft.util.lang.format_sv import *

from mycroft.util.lang.format_fr import nice_number_fr
from mycroft.util.lang.format_fr import nice_time_fr
from mycroft.util.lang.format_fr import pronounce_number_fr


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
    # Convert to spoken representation in appropriate language
    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return nice_number_en(number, speech, denominators)
    elif lang_lower.startswith("pt"):
        return nice_number_pt(number, speech, denominators)
    elif lang_lower.startswith("it"):
        return nice_number_it(number, speech, denominators)
    elif lang_lower.startswith("fr"):
        return nice_number_fr(number, speech, denominators)
    elif lang_lower.startswith("sv"):
        return nice_number_sv(number, speech, denominators)

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
    elif lang_lower.startswith("it"):
        return nice_time_it(dt, speech, use_24hour, use_ampm)
    elif lang_lower.startswith("fr"):
        return nice_time_fr(dt, speech, use_24hour, use_ampm)

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
    elif lang_lower.startswith("it"):
        return pronounce_number_it(number, places=places)
    elif lang_lower.startswith("fr"):
        return pronounce_number_fr(number, places=places)

    # Default to just returning the numeric value
    return str(number)
