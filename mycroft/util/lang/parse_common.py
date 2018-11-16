# -*- coding: utf-8 -*-
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


def is_numeric(input_str):
    """
    Takes in a string and tests to see if it is a number.
    Args:
        text (str): string to test if a number
    Returns:
        (bool): True if a number, else False

    """

    try:
        float(input_str)
        return True
    except ValueError:
        return False


def look_for_fractions(split_list):
    """"
    This function takes a list made by fraction & determines if a fraction.

    Args:
        split_list (list): list created by splitting on '/'
    Returns:
        (bool): False if not a fraction, otherwise True

    """

    if len(split_list) == 2:
        if is_numeric(split_list[0]) and is_numeric(split_list[1]):
            return True

    return False


def extract_numbers_generic(text, pronounce_handler, extract_handler,
                            short_scale=True, ordinals=False):
    """
        Takes in a string and extracts a list of numbers.
        Language agnostic, per language parsers need to be provided

    Args:
        text (str): the string to extract a number from
        pronounce_handler (function): function that pronounces a number
        extract_handler (function): function that extracts the last number
        present in a string
        short_scale (bool): Use "short scale" or "long scale" for large
            numbers -- over a million.  The default is short scale, which
            is now common in most English speaking countries.
            See https://en.wikipedia.org/wiki/Names_of_large_numbers
        ordinals (bool): consider ordinal numbers, e.g. third=3 instead of 1/3
    Returns:
        list: list of extracted numbers as floats
    """
    numbers = []
    normalized = text
    extract = extract_handler(normalized, short_scale, ordinals)
    to_parse = normalized
    while extract:
        numbers.append(extract)
        prev = to_parse
        num_txt = pronounce_handler(extract)
        extract = str(extract)
        if extract.endswith(".0"):
            extract = extract[:-2]

        # handle duplicate occurences, replace last one only
        def replace_right(source, target, replacement, replacements=None):
            return replacement.join(source.rsplit(target, replacements))

        normalized = replace_right(normalized, num_txt, extract, 1)
        # last biggest number was replaced, recurse to handle cases like
        # test one two 3
        to_parse = replace_right(to_parse, num_txt, extract, 1)
        to_parse = replace_right(to_parse, extract, " ", 1)
        if to_parse == prev:
            # avoid infinite loops, occasionally pronounced number may be
            # different from extracted text,
            # ie pronounce(0.5) != half and extract(half) == 0.5
            extract = False
            # TODO fix this
        else:
            extract = extract_handler(to_parse, short_scale, ordinals)
    numbers.reverse()
    return numbers
