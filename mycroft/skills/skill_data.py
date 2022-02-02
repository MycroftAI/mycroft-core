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
"""Handling of skill data such as intents and regular expressions."""

import re
from os import walk
from os.path import splitext, join
from pathlib import Path
from typing import List, Optional

from mycroft.util.format import expand_options
from mycroft.util.log import LOG


class ResourceFileLocator:
    """Locates resource files using a variety of methodologies.

    Attributes:
        skill_directory: the root directory of the skill
        language: the language specified in the device configuration
        locale_directory: the skill's locale directory for the specified language
        dialog_directory: the skill's directory for dialog files
        vocab_directory: the skill's directory for vocabulary files
        regex_directory: the skill's directory for regular expression files
    """

    def __init__(self, skill_directory, language):
        self.skill_directory = skill_directory
        self.language = language
        self.locale_directory = Path(skill_directory, "locale", language)
        self.dialog_directory = self._find_resource_type_directory("dialog")
        self.vocab_directory = self._find_resource_type_directory("vocab")
        self.regex_directory = self._find_resource_type_directory("regex")
        self.gui_directory = self._find_resource_type_directory("ui")

    def _find_resource_type_directory(self, resource_type: str) -> Path:
        """Find the skill's directory for the specified resource type.

        There are three supported methodologies for storing resource files.
        The preferred method is to use the "locale" directory but older methods
        are included in the search for backwards compatibility.  The three
        directory schemes are:
           <skill>/<resource_directory>/<lang>
           <skill>/<resource_directory>
           <skill>/locale/<lang>/.../<res_name>

        Args:
            resource_type: the type of resource file (e.g. 'dialog', 'vocab')

        Returns:
            the skill's directory for the resource type or None if not found
        """
        resource_type_directory = None
        possible_directories = (
            self.locale_directory,
            Path(self.skill_directory, resource_type),
            Path(self.skill_directory, resource_type, self.language),
        )
        for directory in possible_directories:
            if directory.exists():
                resource_type_directory = directory

        return resource_type_directory

    def find_dialog_file(self, file_name: str) -> Optional[str]:
        """Locates a dialog file in the skill's dialog directory.

        Args:
            file_name: the name of the dialog file to search for
        """
        return self._find_resource_file(file_name, self.dialog_directory)

    def find_vocab_file(self, file_name: str) -> Optional[str]:
        """Locates a vocabulary file in the skill's vocab directory.

        Args:
            file_name: the name of the dialog file to search for
        """
        return self._find_resource_file(file_name, self.vocab_directory)

    def find_regex_file(self, file_name: str) -> Optional[str]:
        """Locates a regex file in the skill's regular expressions directory.

        Args:
            file_name: the name of the dialog file to search for
        """
        return self._find_resource_file(file_name, self.regex_directory)

    def find_value_file(self, file_name) -> Optional[str]:
        """Locates a name/value pair file in the skill's dialog directory.

        Args:
            file_name: the name of the dialog file to search for
        """
        return self._find_resource_file(file_name, self.dialog_directory)

    def _find_resource_file(self, file_name: str, directory: Path) -> Optional[str]:
        """Locates a resource file in a directory

        Args:
            file_name: the name of the file to locate
            directory: the directory to look in

        Returns:
            the fully qualified path to the file
        """
        if directory == self.locale_directory:
            file_path = self._find_file_in_locale_directory(file_name)
        else:
            file_path = directory.joinpath(file_name)
            if not file_path.exists():
                file_path = None

        return None if file_path is None else str(file_path)

    def _find_file_in_locale_directory(self, file_name):
        """Locates a resource file in the skill's locale directory.

        A skill's locale directory can contain a subdirectory structure defined
        by the skill author.  Walk the directory and any subdirectories to
        find the resource file.
        """
        file_path = None
        for directory, _, file_names in walk(str(self.locale_directory)):
            if file_name in file_names:
                file_path = Path(directory, file_name)

        return file_path


class Translator:
    """Loads a resource file for the user's configured language.

    Attributes:
        file_locator: instance of the ResourceFileLocator for a skill
        dialog_renderer: instance of the skill's dialog renderer
    """

    def __init__(self, file_locator: ResourceFileLocator, dialog_renderer):
        self.file_locator = file_locator
        self.dialog_renderer = dialog_renderer

    def translate_named_values(self, value_name: str, delimiter=",") -> dict:
        """Load translation file containing names and values.

        Loads a simple delimited file from the skill's "dialog" folder.
        The name is the first item, the value is the second.  Lines prefixed
        with # or // are considered comments and get ignored

        Args:
            value_name: name of the .value file, no extension needed
            delimiter: delimiter character used

        Returns:
            name and value dictionary, or empty dictionary if load fails
        """
        if value_name.endswith(".value"):
            value_file_name = value_name
        else:
            value_file_name = value_name + ".value"
        file_path = self.file_locator.find_value_file(value_file_name)
        named_values = dict()
        if file_path is not None:
            with open(file_path) as value_file:
                for line in [line.strip() for line in value_file.readlines()]:
                    # skip blank or comment lines
                    if not line or line.startswith("#"):
                        continue
                    try:
                        name, value = line.strip().split(delimiter)
                        named_values[name] = value
                    except ValueError:
                        LOG.exception(
                            f"Failed to load value file {value_name} "
                            f"record containing {line}"
                        )

        return named_values

    def translate_dialog(self, dialog_name: str, data: dict = None) -> str:
        """Load a random line from a dialog translation file.

        The dialog is randomly chosen from the file.  Named variables in the
        dialog are populated with values found in the data dictionary.

        Args:
            dialog_name: name of the dialog file (no extension needed)
            data: keyword arguments used to populate dialog variables

        Returns:
            A randomly chosen dialog
        """
        return self.dialog_renderer.render(dialog_name, data or {})

    def translate_list(self, list_name, data=None) -> List[str]:
        """Load a translation file containing a list of words or phrases

        Named variables in the dialog are populated with values found in the
        data dictionary.

        Args:
            list_name (str): name of the list file (no extension needed)
            data: keyword arguments used to populate variables

        Returns:
            List of words or phrases read from the list file.
        """
        return self._translate_dialog_file(list_name + ".list", data)

    def translate_template(self, template_name, data=None) -> List[str]:
        """Load a translatable template.

        Named variables in the dialog are populated with values found in the
        data dictionary.

        Args:
            template_name: the name of the template file (no extension needed)
            data: keyword arguments used to populate variables

        Returns:
            The loaded template file
        """
        return self._translate_dialog_file(template_name + ".template", data)

    def _translate_dialog_file(self, file_name, data=None) -> List[str]:
        """Load and lines from a file and populate the variables.

        Args:
            file_name: the name of the dialog file to read
            data: keyword arguments used to populate variables

        Returns:
            Contents of the file with variables resolved.
        """
        dialogs = None
        file_path = self.file_locator.find_dialog_file(file_name)
        if file_path is not None:
            dialogs = []
            with open(file_path) as dialog_file:
                for line in [line.strip() for line in dialog_file.readlines()]:
                    line = line.replace("{{", "{").replace("}}", "}")
                    if data is not None:
                        line = line.format(**data)
                    dialogs.append(line)

        return dialogs


class RegexExtractor:
    """Extracts data from an utterance using regular expressions."""

    def __init__(self, file_finder, regex_name):
        self.regex_file_path = file_finder.find_regex_file(regex_name + ".rx")
        self.group_name = regex_name

    def extract(self, utterance) -> Optional[str]:
        """Attempt to find a value in a user request.

        Args:
            utterance: request spoken by the user

        Returns:
            The value extracted from the utterance, if found
        """
        extract = None
        if self.regex_file_path:
            regex_patterns = self._get_search_patterns()
            pattern_match = self._match_utterance_to_patterns(utterance, regex_patterns)
            if pattern_match is not None:
                extract = self._extract_group_from_match(pattern_match)
        self._log_extraction_result(extract)

        return extract

    def _get_search_patterns(self) -> List[str]:
        """Read a file containing one or more regular expressions.

        Returns:
            list of regular expression patterns to match against.
        """
        regex_patterns = []
        with open(self.regex_file_path) as regex_file:
            for pattern in [line.strip() for line in regex_file.readlines()]:
                if pattern and pattern[0] != "#":
                    regex_patterns.append(pattern)

        return regex_patterns

    @staticmethod
    def _match_utterance_to_patterns(utterance: str, regex_patterns: List[str]):
        """Match regular expressions to user request.

        Args:
            utterance: request spoken by the user
            regex_patterns: regular expressions read from a .rx file

        Returns:
            a regular expression match object if a match is found
        """
        pattern_match = None
        for pattern in regex_patterns:
            pattern_match = re.search(pattern, utterance)
            if pattern_match:
                break

        return pattern_match

    def _extract_group_from_match(self, pattern_match):
        """Extract the alarm name from the utterance.

        Args:
            pattern_match: a regular expression match object
        """
        extract = None
        try:
            extract = pattern_match.group(self.group_name).strip()
        except IndexError:
            pass

        return extract

    def _log_extraction_result(self, extract: str):
        """Log the results of the matching.

        Args:
            extract: the value extracted from the user utterance
        """
        if extract is None:
            LOG.info(f"No {self.group_name.lower()} extracted from utterance")
        else:
            LOG.info(f"{self.group_name} extracted from utterance: " + extract)


def read_vocab_file(path):
    """Read a vocabulary file.

    This reads a .voc file, stripping out empty lines comments and expand
    parentheses. It returns each line as a list of all expanded
    alternatives.

    Args:
        path (str): path to vocab file.

    Returns:
        List of Lists of strings.
    """
    vocab = []
    with open(path, "r", encoding="utf8") as voc_file:
        for line in voc_file.readlines():
            if line.startswith("#") or line.strip() == "":
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
    if path.endswith(".rx"):
        with open(path, "r", encoding="utf8") as reg_file:
            for line in reg_file.readlines():
                if line.startswith("#"):
                    continue
                LOG.debug("regex pre-munge: " + line.strip())
                regex = munge_regex(line.strip(), skill_id)
                LOG.debug("regex post-munge: " + regex)
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
    return "".join(c if c.isalnum() else "_" for c in str(skill_id))


def munge_regex(regex, skill_id):
    """Insert skill id as letters into match groups.

    Args:
        regex (str): regex string
        skill_id (str): skill identifier
    Returns:
        (str) munged regex
    """
    base = "(?P<" + to_alnum(skill_id)
    return base.join(regex.split("(?P<"))


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
    if not name.startswith(str(skill_id) + ":"):
        intent_parser.name = str(skill_id) + ":" + name
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
        element = [skill_id + e.replace(skill_id, "") for e in i]
        at_least_one.append(tuple(element))
    intent_parser.at_least_one = at_least_one
