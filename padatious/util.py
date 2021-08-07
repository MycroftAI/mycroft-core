# Copyright 2017 Mycroft AI, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from xxhash import xxh32
from padatious.bracket_expansion import SentenceTreeParser


def lines_hash(lines):
    """
    Creates a unique binary id for the given lines
    Args:
        lines (list<str>): List of strings that should be collectively hashed
    Returns:
        bytearray: Binary hash
    """
    x = xxh32()
    for i in lines:
        x.update(i.encode())
    return x.digest()


def tokenize(sentence):
    """
    Converts a single sentence into a list of individual significant units
    Args:
        sentence (str): Input string ie. 'This is a sentence.'
    Returns:
        list<str>: List of tokens ie. ['this', 'is', 'a', 'sentence']
    """
    tokens = []

    class Vars:
        start_pos = -1
        last_type = 'o'

    def update(c, i):
        if c.isalpha() or c in '-{}':
            t = 'a'
        elif c.isdigit() or c == '#':
            t = 'n'
        elif c.isspace():
            t = 's'
        else:
            t = 'o'

        if t != Vars.last_type or t == 'o':
            if Vars.start_pos >= 0:
                token = sentence[Vars.start_pos:i].lower()
                if token not in '.!?':
                    tokens.append(token)
            Vars.start_pos = -1 if t == 's' else i
        Vars.last_type = t

    for i, char in enumerate(sentence):
        update(char, i)
    update(' ', len(sentence))
    return tokens


def expand_parentheses(sent):
    """
    ['1', '(', '2', '|', '3, ')'] -> [['1', '2'], ['1', '3']]
    For example:

    Will it (rain|pour) (today|tomorrow|)?

    ---->

    Will it rain today?
    Will it rain tomorrow?
    Will it rain?
    Will it pour today?
    Will it pour tomorrow?
    Will it pour?

    Args:
        sent (list<str>): List of tokens in sentence
    Returns:
        list<list<str>>: Multiple possible sentences from original
    """
    return SentenceTreeParser(sent).expand_parentheses()


def remove_comments(lines):
    return [i for i in lines if not i.startswith('//')]


def resolve_conflicts(inputs, outputs):
    """
    Checks for duplicate inputs and if there are any,
    remove one and set the output to the max of the two outputs
    Args:
        inputs (list<list<float>>): Array of input vectors
        outputs (list<list<float>>): Array of output vectors
    Returns:
        tuple<inputs, outputs>: The modified inputs and outputs
    """
    data = {}
    for inp, out in zip(inputs, outputs):
        tup = tuple(inp)
        if tup in data:
            data[tup].append(out)
        else:
            data[tup] = [out]

    inputs, outputs = [], []
    for inp, outs in data.items():
        inputs.append(list(inp))
        combined = [0] * len(outs[0])
        for i in range(len(combined)):
            combined[i] = max(j[i] for j in outs)
        outputs.append(combined)
    return inputs, outputs


class StrEnum(object):
    """Enum with strings as keys. Implements items method"""
    @classmethod
    def values(cls):
        return [getattr(cls, i) for i in dir(cls)
                if not i.startswith("__") and i != 'values']
