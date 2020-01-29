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

This file imports the main functions from lingua franca providing a layer
for convenience.
"""

from difflib import SequenceMatcher

# These are the main functions of lingua franca parsing offered here for
# convenience.
import lingua_franca.parse

from lingua_franca.lang import get_primary_lang_code, get_active_lang

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

from .time import now_local
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
    return lingua_franca.parse.extract_numbers(text, short_scale,
                                               ordinals, lang)


def extract_number(text, short_scale=True, ordinals=False, lang=None):
    """Takes in a string and extracts a number.
    Args:
        text (str): the string to extract a number from
        short_scale (bool): Use "short scale" or "long scale" for large
            numbers -- over a million.  The default is short scale, which
            is now common in most English speaking countries.
            See https://en.wikipedia.org/wiki/Names_of_large_numbers
        ordinals (bool): consider ordinal numbers, e.g. third=3 instead of 1/3
        lang (str): the BCP-47 code for the language to use, None uses default
    Returns:
        (int, float or False): The number extracted or False if the input
                               text contains no numbers
    """
    return lingua_franca.parse.extract_number(text, short_scale,
                                              ordinals, lang)


def normalize(text, lang=None, remove_articles=True):
    """Prepare a string for parsing
    This function prepares the given text for parsing by making
    numbers consistent, getting rid of contractions, etc.
    Args:
        text (str): the string to normalize
        lang (str): the BCP-47 code for the language to use, None uses default
        remove_articles (bool): whether to remove articles (like 'a', or
                                'the'). True by default.
    Returns:
        (str): The normalized string.
    """
    return lingua_franca.parse.normalize(text, lang, remove_articles)


def extract_datetime(text, anchorDate=None, lang=None, default_time=None):
    """Extracts date and time information from a sentence.

    Parses many of the common ways that humans express dates and times,
    including relative dates like "5 days from today", "tomorrow', and
    "Tuesday".

    Vague terminology are given arbitrary values, like:
        - morning = 8 AM
        - afternoon = 3 PM
        - evening = 7 PM
    If a time isn't supplied or implied, the function defaults to 12 AM
    Args:
        text (str): the text to be interpreted
        anchorDate (:obj:`datetime`, optional): the date to be used for
            relative dating (for example, what does "tomorrow" mean?).
            Defaults to the current local date/time.
        lang (str): the BCP-47 code for the language to use, None uses default
        default_time (datetime.time): time to use if none was found in
            the input string.
    Returns:
        [:obj:`datetime`, :obj:`str`]: 'datetime' is the extracted date
            as a datetime object in the user's local timezone.
            'leftover_string' is the original phrase with all date and time
            related keywords stripped out. See examples for further
            clarification
            Returns 'None' if no date or time related text is found.
    Examples:
        >>> extract_datetime(
        ... "What is the weather like the day after tomorrow?",
        ... datetime(2017, 06, 30, 00, 00)
        ... )
        [datetime.datetime(2017, 7, 2, 0, 0), 'what is weather like']
        >>> extract_datetime(
        ... "Set up an appointment 2 weeks from Sunday at 5 pm",
        ... datetime(2016, 02, 19, 00, 00)
        ... )
        [datetime.datetime(2016, 3, 6, 17, 0), 'set up appointment']
        >>> extract_datetime(
        ... "Set up an appointment",
        ... datetime(2016, 02, 19, 00, 00)
        ... )
        None
    """
    ret = lingua_franca.parse.extract_datetime(text, anchorDate or now_local(),
                                               lang, default_time)

    # TODO: When default skills work with the documented behavour below needs
    # to be removed.
    # This implements the incorrect return value expected by many skills
    lang = lang or get_active_lang()
    if ret is None and lang == 'en-us':
        ret = (anchorDate or
               now_local().replace(hour=0, minute=0, second=0, microsecond=0),
               text)

    return ret


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


def get_gender(word, context="", lang=None):
    """ Guess the gender of a word
    Some languages assign genders to specific words.  This method will attempt
    to determine the gender, optionally using the provided context sentence.
    Args:
        word (str): The word to look up
        context (str, optional): String containing word, for context
        lang (str): the BCP-47 code for the language to use, None uses default
    Returns:
        str: The code "m" (male), "f" (female) or "n" (neutral) for the gender,
             or None if unknown/or unused in the given language.
    """
    return lingua_franca.parse.get_gender(word, context, lang)
