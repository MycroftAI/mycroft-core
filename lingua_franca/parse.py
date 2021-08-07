#
# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from difflib import SequenceMatcher
from warnings import warn
from lingua_franca.time import now_local
from lingua_franca.internal import populate_localized_function_dict, \
    get_active_langs, get_full_lang_code, get_primary_lang_code, \
    get_default_lang, localized_function, _raise_unsupported_language

_REGISTERED_FUNCTIONS = ("extract_numbers",
                         "extract_number",
                         "extract_duration",
                         "extract_datetime",
                         "normalize",
                         "get_gender",
                         "is_fractional",
                         "is_ordinal")

populate_localized_function_dict("parse", langs=get_active_langs())


def fuzzy_match(x: str, against: str) -> float:
    """Perform a 'fuzzy' comparison between two strings.

    Returns:
        match percentage -- 1.0 for perfect match,
        down to 0.0 for no match at all.
    """
    return SequenceMatcher(None, x, against).ratio()


def match_one(query, choices):
    """
        Find best match from a list or dictionary given an input

        Args:
            query (str): string to test
            choices (list): list or dictionary of choices

        Returns:
            tuple: (best match, score)
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


@localized_function()
def extract_numbers(text, short_scale=True, ordinals=False, lang=''):
    """
        Takes in a string and extracts a list of numbers.

    Args:
        text (str): the string to extract a number from
        short_scale (bool): Use "short scale" or "long scale" for large
            numbers -- over a million.  The default is short scale, which
            is now common in most English speaking countries.
            See https://en.wikipedia.org/wiki/Names_of_large_numbers
        ordinals (bool): consider ordinal numbers, e.g. third=3 instead of 1/3
        lang (str, optional): an optional BCP-47 language code, if omitted
                              the default language will be used.
    Returns:
        list: list of extracted numbers as floats, or empty list if none found
    """


@localized_function()
def extract_number(text, short_scale=True, ordinals=False, lang=''):
    """Takes in a string and extracts a number.

    Args:
        text (str): the string to extract a number from
        short_scale (bool): Use "short scale" or "long scale" for large
            numbers -- over a million.  The default is short scale, which
            is now common in most English speaking countries.
            See https://en.wikipedia.org/wiki/Names_of_large_numbers
        ordinals (bool): consider ordinal numbers, e.g. third=3 instead of 1/3
        lang (str, optional): an optional BCP-47 language code, if omitted
                              the default language will be used.
    Returns:
        (int, float or False): The number extracted or False if the input
                               text contains no numbers
    """


@localized_function()
def extract_duration(text, lang=''):
    """ Convert an english phrase into a number of seconds

    Convert things like:

    * "10 minute"
    * "2 and a half hours"
    * "3 days 8 hours 10 minutes and 49 seconds"

    into an int, representing the total number of seconds.

    The words used in the duration will be consumed, and
    the remainder returned.

    As an example, "set a timer for 5 minutes" would return
    ``(300, "set a timer for")``.

    Args:
        text (str): string containing a duration
        lang (str, optional): an optional BCP-47 language code, if omitted
                              the default language will be used.

    Returns:
        (timedelta, str):
                    A tuple containing the duration and the remaining text
                    not consumed in the parsing. The first value will
                    be None if no duration is found. The text returned
                    will have whitespace stripped from the ends.
    """


@localized_function()
def extract_datetime(text, anchorDate=None, lang='', default_time=None):
    """
    Extracts date and time information from a sentence.  Parses many of the
    common ways that humans express dates and times, including relative dates
    like "5 days from today", "tomorrow', and "Tuesday".

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
        ... datetime(2017, 6, 30, 00, 00)
        ... )
        [datetime.datetime(2017, 7, 2, 0, 0), 'what is weather like']

        >>> extract_datetime(
        ... "Set up an appointment 2 weeks from Sunday at 5 pm",
        ... datetime(2016, 2, 19, 00, 00)
        ... )
        [datetime.datetime(2016, 3, 6, 17, 0), 'set up appointment']

        >>> extract_datetime(
        ... "Set up an appointment",
        ... datetime(2016, 2, 19, 00, 00)
        ... )
        None
    """


@localized_function()
def normalize(text, lang='', remove_articles=True):
    """Prepare a string for parsing

    This function prepares the given text for parsing by making
    numbers consistent, getting rid of contractions, etc.

    Args:
        text (str): the string to normalize
        lang (str, optional): an optional BCP-47 language code, if omitted
                              the default language will be used.
        remove_articles (bool): whether to remove articles (like 'a', or
                                'the'). True by default.

    Returns:
        (str): The normalized string.
    """


@localized_function()
def get_gender(word, context="", lang=''):
    """ Guess the gender of a word

    Some languages assign genders to specific words.  This method will attempt
    to determine the gender, optionally using the provided context sentence.

    Args:
        word (str): The word to look up
        context (str, optional): String containing word, for context
        lang (str, optional): an optional BCP-47 language code, if omitted
                              the default language will be used.

    Returns:
        str: The code "m" (male), "f" (female) or "n" (neutral) for the gender,
             or None if unknown/or unused in the given language.
    """


@localized_function()
def is_fractional(input_str, short_scale=True, lang=''):
    """
    This function takes the given text and checks if it is a fraction.
    Used by most of the number exractors.

    Will return False on phrases that *contain* a fraction. Only detects
    exact matches. To pull a fraction from a string, see extract_number()

    Args:
        input_str (str): the string to check if fractional
        short_scale (bool): use short scale if True, long scale if False
        lang (str, optional): an optional BCP-47 language code, if omitted
                              the default language will be used.
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction
    """


@localized_function()
def is_ordinal(input_str, lang=''):
    """
    This function takes the given text and checks if it is an ordinal number.

    Args:
        input_str (str): the string to check if ordinal
        lang (str, optional): an optional BCP-47 language code, if omitted
                              the default language will be used.
    Returns:
        (bool) or (float): False if not an ordinal, otherwise the number
        corresponding to the ordinal
    """
