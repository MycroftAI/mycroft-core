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
The mycroft.util.parse module provides various parsing functions for
things like numbers, times, durations etc.

The focus of these parsing functions is to extract data from natural speech
and to allow localization.

This file imports the main functions from lingua franca providing a
compatibility layer.
"""

from difflib import SequenceMatcher

from lingua_franca.parse import (extract_number, extract_datetime, normalize,
                                 get_gender)
from lingua_franca.lang import get_primary_lang_code

# TODO: Remove all imports below from lingua_franca.lang in v20.02
from lingua_franca.lang.parse_en import *
from lingua_franca.lang.parse_pt import *
from lingua_franca.lang.parse_es import *
from lingua_franca.lang.parse_it import *
from lingua_franca.lang.parse_sv import *

from lingua_franca.lang.parse_de import extractnumber_de
from lingua_franca.lang.parse_de import extract_numbers_de
from lingua_franca.lang.parse_de import extract_datetime_de
from lingua_franca.lang.parse_de import normalize_de
from lingua_franca.lang.parse_fr import extractnumber_fr
from lingua_franca.lang.parse_fr import extract_numbers_fr
from lingua_franca.lang.parse_fr import extract_datetime_fr
from lingua_franca.lang.parse_fr import normalize_fr
from lingua_franca.lang.parse_da import extractnumber_da
from lingua_franca.lang.parse_da import extract_numbers_da
from lingua_franca.lang.parse_da import extract_datetime_da
from lingua_franca.lang.parse_da import normalize_da
from lingua_franca.lang.parse_nl import extractnumber_nl
from lingua_franca.lang.parse_nl import extract_datetime_nl
from lingua_franca.lang.parse_nl import normalize_nl

from .log import LOG


def _log_unsupported_language(language, supported_languages):
    """
    Log a warning when a language is unsupported

    Arguments:
        language: str
            The language that was supplied.
        supported_languages: [str]
            The list of supported languages.
    """
    supported = ' '.join(supported_languages)
    LOG.warning('Language "{language}" not recognized! Please make sure your '
                'language is one of the following: {supported}.'
                .format(language=language, supported=supported))


def fuzzy_match(x, against):
    """Perform a 'fuzzy' comparison between two strings.
    Returns:
        float: match percentage -- 1.0 for perfect match,
               down to 0.0 for no match at all.
    """
    return SequenceMatcher(None, x, against).ratio()


def match_one(query, choices):
    """
        Find best match from a list or dictionary given an input

        Arguments:
            query:   string to test
            choices: list or dictionary of choices

        Returns: tuple with best match, score
    """
    if isinstance(choices, dict):
        _choices = list(choices.keys())
    elif isinstance(choices, list):
        _choices = choices
    else:
        raise ValueError('a list or dict of choices must be provided')

    best = (_choices[0], fuzzy_match(query, _choices[0]))
    for c in _choices[1:]:
        score = fuzzy_match(query, c)
        if score > best[1]:
            best = (c, score)

    if isinstance(choices, dict):
        return (choices[best[0]], best[1])
    else:
        return best


def extract_numbers(text, short_scale=True, ordinals=False, lang=None):
    """
        Takes in a string and extracts a list of numbers.

    Args:
        text (str): the string to extract a number from
        short_scale (bool): Use "short scale" or "long scale" for large
            numbers -- over a million.  The default is short scale, which
            is now common in most English speaking countries.
            See https://en.wikipedia.org/wiki/Names_of_large_numbers
        ordinals (bool): consider ordinal numbers, e.g. third=3 instead of 1/3
        lang (str): the BCP-47 code for the language to use, None uses default
    Returns:
        list: list of extracted numbers as floats, or empty list if none found
    """
    lang_code = get_primary_lang_code(lang)
    if lang_code == "en":
        return extract_numbers_en(text, short_scale, ordinals)
    elif lang_code == "de":
        return extract_numbers_de(text, short_scale, ordinals)
    elif lang_code == "fr":
        return extract_numbers_fr(text, short_scale, ordinals)
    elif lang_code == "it":
        return extract_numbers_it(text, short_scale, ordinals)
    elif lang_code == "da":
        return extract_numbers_da(text, short_scale, ordinals)
    elif lang_code == "es":
        return extract_numbers_es(text, short_scale, ordinals)
    return []


def extract_duration(text, lang=None):
    """ Convert an english phrase into a number of seconds

    Convert things like:
        "10 minute"
        "2 and a half hours"
        "3 days 8 hours 10 minutes and 49 seconds"
    into an int, representing the total number of seconds.

    The words used in the duration will be consumed, and
    the remainder returned.

    As an example, "set a timer for 5 minutes" would return
    (300, "set a timer for").

    Args:
        text (str): string containing a duration
        lang (str): the BCP-47 code for the language to use, None uses default

    Returns:
        (timedelta, str):
                    A tuple containing the duration and the remaining text
                    not consumed in the parsing. The first value will
                    be None if no duration is found. The text returned
                    will have whitespace stripped from the ends.
    """
    lang_code = get_primary_lang_code(lang)

    if lang_code == "en":
        return extract_duration_en(text)

    # TODO: extract_duration for other languages
    _log_unsupported_language(lang_code, ['en'])
    return None
