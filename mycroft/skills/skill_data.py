# Copyright 2018 Mycroft AI Inc.
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

"""Functions to load skill data such as intents and regular expressions."""

import collections
import csv
import re
from os import walk
from os.path import splitext, join

from mycroft.util.format import expand_options
from mycroft.util.log import LOG


def read_vocab_file(path):
    """ Read voc file.

        This reads a .voc file, stripping out empty lines comments and expand
        parentheses. It returns each line as a list of all expanded
        alternatives.

        Args:
            path (str): path to vocab file.

        Returns:
            List of Lists of strings.
    """
    vocab = []
    with open(path, 'r', encoding='utf8') as voc_file:
        for line in voc_file.readlines():
            if line.startswith('#') or line.strip() == '':
                continue
            vocab.append(expand_options(line.lower()))
    return vocab


def load_regex_from_file(path, skill_id):
    """Load regex from file
    The regex is sent to the intent handler using the message bus

    Args:
        path:       path to vocabulary file (*.voc)
        skill_id:   skill_id to the regex is tied to
    """
    regexes = []
    if path.endswith('.rx'):
        with open(path, 'r', encoding='utf8') as reg_file:
            for line in reg_file.readlines():
                if line.startswith("#"):
                    continue
                LOG.debug('regex pre-munge: ' + line.strip())
                regex = munge_regex(line.strip(), skill_id)
                LOG.debug('regex post-munge: ' + regex)
                # Raise error if regex can't be compiled
                re.compile(regex)
                regexes.append(regex)

    return regexes


def load_vocabulary(basedir, skill_id):
    """Load vocabulary from all files in the specified directory.

    Args:
        basedir (str): path of directory to load from (will recurse)
        skill_id: skill the data belongs to
    Returns:
        dict with intent_type as keys and list of list of lists as value.
    """
    vocabs = {}
    for path, _, files in walk(basedir):
        for f in files:
            if f.endswith(".voc"):
                vocab_type = to_alnum(skill_id) + splitext(f)[0]
                vocs = read_vocab_file(join(path, f))
                if vocs:
                    vocabs[vocab_type] = vocs
    return vocabs


def load_regex(basedir, skill_id):
    """Load regex from all files in the specified directory.

    Args:
        basedir (str): path of directory to load from
        bus (messagebus emitter): messagebus instance used to send the vocab to
                                  the intent service
        skill_id (str): skill identifier
    """
    regexes = []
    for path, _, files in walk(basedir):
        for f in files:
            if f.endswith(".rx"):
                regexes += load_regex_from_file(join(path, f), skill_id)
    return regexes


def to_alnum(skill_id):
    """Convert a skill id to only alphanumeric characters

     Non alpha-numeric characters are converted to "_"

    Args:
        skill_id (str): identifier to be converted
    Returns:
        (str) String of letters
    """
    return ''.join(c if c.isalnum() else '_' for c in str(skill_id))


def munge_regex(regex, skill_id):
    """Insert skill id as letters into match groups.

    Args:
        regex (str): regex string
        skill_id (str): skill identifier
    Returns:
        (str) munged regex
    """
    base = '(?P<' + to_alnum(skill_id)
    return base.join(regex.split('(?P<'))


def munge_intent_parser(intent_parser, name, skill_id):
    """Rename intent keywords to make them skill exclusive
    This gives the intent parser an exclusive name in the
    format <skill_id>:<name>.  The keywords are given unique
    names in the format <Skill id as letters><Intent name>.

    The function will not munge instances that's already been
    munged

    Args:
        intent_parser: (IntentParser) object to update
        name: (str) Skill name
        skill_id: (int) skill identifier
    """
    # Munge parser name
    if not name.startswith(str(skill_id) + ':'):
        intent_parser.name = str(skill_id) + ':' + name
    else:
        intent_parser.name = name

    # Munge keywords
    skill_id = to_alnum(skill_id)
    # Munge required keyword
    reqs = []
    for i in intent_parser.requires:
        if not i[0].startswith(skill_id):
            kw = (skill_id + i[0], skill_id + i[0])
            reqs.append(kw)
        else:
            reqs.append(i)
    intent_parser.requires = reqs

    # Munge optional keywords
    opts = []
    for i in intent_parser.optional:
        if not i[0].startswith(skill_id):
            kw = (skill_id + i[0], skill_id + i[0])
            opts.append(kw)
        else:
            opts.append(i)
    intent_parser.optional = opts

    # Munge at_least_one keywords
    at_least_one = []
    for i in intent_parser.at_least_one:
        element = [skill_id + e.replace(skill_id, '') for e in i]
        at_least_one.append(tuple(element))
    intent_parser.at_least_one = at_least_one


def read_value_file(filename, delim):
    """Read value file.

    The value file is a simple csv structure with a key and value.

    Args:
        filename (str): file to read
        delim (str): csv delimiter

    Returns:
        OrderedDict with results.
    """
    result = collections.OrderedDict()

    if filename:
        with open(filename) as f:
            reader = csv.reader(f, delimiter=delim)
            for row in reader:
                # skip blank or comment lines
                if not row or row[0].startswith("#"):
                    continue
                if len(row) != 2:
                    continue

                result[row[0]] = row[1]
    return result


def read_translated_file(filename, data):
    """Read a file inserting data.

    Args:
        filename (str): file to read
        data (dict): dictionary with data to insert into file

    Returns:
        list of lines.
    """
    if filename:
        with open(filename) as f:
            text = f.read().replace('{{', '{').replace('}}', '}')
            return text.format(**data or {}).rstrip('\n').split('\n')
    else:
        return None
