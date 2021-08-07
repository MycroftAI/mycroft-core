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
from collections import namedtuple
import re


class Normalizer:
    """
    individual languages may subclass this if needed

    normalize_XX should pass a valid config read from json
    """
    _default_config = {}

    def __init__(self, config=None):
        self.config = config or self._default_config

    @staticmethod
    def tokenize(utterance):
        # Split things like 12%
        utterance = re.sub(r"([0-9]+)([\%])", r"\1 \2", utterance)
        # Split thins like #1
        utterance = re.sub(r"(\#)([0-9]+\b)", r"\1 \2", utterance)
        return utterance.split()

    @property
    def should_lowercase(self):
        return self.config.get("lowercase", False)

    @property
    def should_numbers_to_digits(self):
        return self.config.get("numbers_to_digits", True)

    @property
    def should_expand_contractions(self):
        return self.config.get("expand_contractions", True)

    @property
    def should_remove_symbols(self):
        return self.config.get("remove_symbols", False)

    @property
    def should_remove_accents(self):
        return self.config.get("remove_accents", False)

    @property
    def should_remove_articles(self):
        return self.config.get("remove_articles", False)

    @property
    def should_remove_stopwords(self):
        return self.config.get("remove_stopwords", False)

    @property
    def contractions(self):
        return self.config.get("contractions", {})

    @property
    def word_replacements(self):
        return self.config.get("word_replacements", {})

    @property
    def number_replacements(self):
        return self.config.get("number_replacements", {})

    @property
    def accents(self):
        return self.config.get("accents",
                               {"á": "a", "à": "a", "ã": "a", "â": "a",
                                "é": "e", "è": "e", "ê": "e", "ẽ": "e",
                                "í": "i", "ì": "i", "î": "i", "ĩ": "i",
                                "ò": "o", "ó": "o", "ô": "o", "õ": "o",
                                "ú": "u", "ù": "u", "û": "u", "ũ": "u",
                                "Á": "A", "À": "A", "Ã": "A", "Â": "A",
                                "É": "E", "È": "E", "Ê": "E", "Ẽ": "E",
                                "Í": "I", "Ì": "I", "Î": "I", "Ĩ": "I",
                                "Ò": "O", "Ó": "O", "Ô": "O", "Õ": "O",
                                "Ú": "U", "Ù": "U", "Û": "U", "Ũ": "U"
                                })

    @property
    def stopwords(self):
        return self.config.get("stopwords", [])

    @property
    def articles(self):
        return self.config.get("articles", [])

    @property
    def symbols(self):
        return self.config.get("symbols",
                               [";", "_", "!", "?", "<", ">",
                                "|", "(", ")", "=", "[", "]", "{",
                                "}", "»", "«", "*", "~", "^", "`"])

    def expand_contractions(self, utterance):
        """ Expand common contractions, e.g. "isn't" -> "is not" """
        words = self.tokenize(utterance)
        for idx, w in enumerate(words):
            if w in self.contractions:
                words[idx] = self.contractions[w]
        utterance = " ".join(words)
        return utterance

    def numbers_to_digits(self, utterance):
        words = self.tokenize(utterance)
        for idx, w in enumerate(words):
            if w in self.number_replacements:
                words[idx] = self.number_replacements[w]
        utterance = " ".join(words)
        return utterance

    def remove_articles(self, utterance):
        words = self.tokenize(utterance)
        for idx, w in enumerate(words):
            if w in self.articles:
                words[idx] = ""
        utterance = " ".join(words)
        return utterance

    def remove_stopwords(self, utterance):
        words = self.tokenize(utterance)
        for idx, w in enumerate(words):
            if w in self.stopwords:
                words[idx] = ""
        # if words[-1] == '-':
        #    words = words[:-1]
        utterance = " ".join(words)
        # Remove trailing whitespaces from utterance along with orphaned
        # hyphens, more characters may be added later
        utterance = re.sub(r'- *$', '', utterance)
        return utterance

    def remove_symbols(self, utterance):
        for s in self.symbols:
            utterance = utterance.replace(s, " ")
        return utterance

    def remove_accents(self, utterance):
        for s in self.accents:
            utterance = utterance.replace(s, self.accents[s])
        return utterance

    def replace_words(self, utterance):
        words = self.tokenize(utterance)
        for idx, w in enumerate(words):
            if w in self.word_replacements:
                words[idx] = self.word_replacements[w]
        utterance = " ".join(words)
        return utterance

    def normalize(self, utterance="", remove_articles=None):
        # mutations
        if self.should_lowercase:
            utterance = utterance.lower()
        if self.should_expand_contractions:
            utterance = self.expand_contractions(utterance)
        if self.should_numbers_to_digits:
            utterance = self.numbers_to_digits(utterance)
        utterance = self.replace_words(utterance)

        # removals
        if self.should_remove_symbols:
            utterance = self.remove_symbols(utterance)
        if self.should_remove_accents:
            utterance = self.remove_accents(utterance)
        # TODO deprecate remove_articles param, backwards compat
        if remove_articles is not None and remove_articles:
            utterance = self.remove_articles(utterance)
        elif self.should_remove_articles:
            utterance = self.remove_articles(utterance)
        if self.should_remove_stopwords:
            utterance = self.remove_stopwords(utterance)
        # remove extra spaces
        utterance = " ".join([w for w in utterance.split(" ") if w])
        return utterance


# Token is intended to be used in the number processing functions in
# this module. The parsing requires slicing and dividing of the original
# text. To ensure things parse correctly, we need to know where text came
# from in the original input, hence this nametuple.
Token = namedtuple('Token', 'word index')


class ReplaceableNumber:
    """
    Similar to Token, this class is used in number parsing.

    Once we've found a number in a string, this class contains all
    the info about the value, and where it came from in the original text.
    In other words, it is the text, and the number that can replace it in
    the string.
    """

    def __init__(self, value, tokens: [Token]):
        self.value = value
        self.tokens = tokens

    def __bool__(self):
        return bool(self.value is not None and self.value is not False)

    @property
    def start_index(self):
        return self.tokens[0].index

    @property
    def end_index(self):
        return self.tokens[-1].index

    @property
    def text(self):
        return ' '.join([t.word for t in self.tokens])

    def __setattr__(self, key, value):
        try:
            getattr(self, key)
        except AttributeError:
            super().__setattr__(key, value)
        else:
            raise Exception("Immutable!")

    def __str__(self):
        return "({v}, {t})".format(v=self.value, t=self.tokens)

    def __repr__(self):
        return "{n}({v}, {t})".format(n=self.__class__.__name__, v=self.value,
                                      t=self.tokens)


def tokenize(text):
    """
    Generate a list of token object, given a string.
    Args:
        text str: Text to tokenize.

    Returns:
        [Token]

    """
    return [Token(word, index)
            for index, word in enumerate(Normalizer.tokenize(text))]


def partition_list(items, split_on):
    """
    Partition a list of items.

    Works similarly to str.partition

    Args:
        items:
        split_on callable:
            Should return a boolean. Each item will be passed to
            this callable in succession, and partitions will be
            created any time it returns True.

    Returns:
        [[any]]

    """
    splits = []
    current_split = []
    for item in items:
        if split_on(item):
            splits.append(current_split)
            splits.append([item])
            current_split = []
        else:
            current_split.append(item)
    splits.append(current_split)
    return list(filter(lambda x: len(x) != 0, splits))


def invert_dict(original):
    """
    Produce a dictionary with the keys and values
    inverted, relative to the dict passed in.

    Args:
        original dict: The dict like object to invert

    Returns:
        dict

    """
    return {value: key for key, value in original.items()}


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
