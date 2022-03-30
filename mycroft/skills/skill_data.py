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
from collections import namedtuple

from os import walk
from pathlib import Path
from typing import List, Optional, Tuple

from mycroft.util.file_utils import resolve_resource_file
from mycroft.util.format import expand_options
from mycroft.util.log import LOG

SkillResourceTypes = namedtuple(
    "SkillResourceTypes",
    [
        "dialog",
        "entity",
        "intent",
        "list",
        "named_value",
        "regex",
        "template",
        "vocabulary",
        "word",
    ],
)


class ResourceType:
    """Defines the attributes of a type of skill resource.

    Examples:
        dialog = ResourceType("dialog", ".dialog")
        dialog.locate_base_directory(self.root_dir, self.lang)

        named_value = ResourceType("named_value", ".value")
        named_value.locate_base_directory(self.root_dir, self.lang)

    Attributes:
        resource_type: one of a predefined set of resource types for skills
        file_extension: the file extension associated with the resource type
        base_directory: directory containing all files for the resource type
    """

    def __init__(self, resource_type: str, file_extension: str, language: str):
        self.resource_type = resource_type
        self.file_extension = file_extension
        self.language = language
        self.base_directory = None

    def locate_base_directory(self, skill_directory):
        """Find the skill's base directory for the specified resource type.

        There are three supported methodologies for storing resource files.
        The preferred method is to use the "locale" directory but older methods
        are included in the search for backwards compatibility.  The three
        directory schemes are:
           <skill>/locale/<lang>/.../<resource_type>
           <skill>/<resource_subdirectory>/<lang>/
           <skill>/<resource_subdirectory>
        If the directory for the specified language doesn't exist, fall back to
        the default "en-us".

        Args:
            skill_directory: the root directory of a skill
        Returns:
            the skill's directory for the resource type or None if not found
        """
        resource_subdirectory = self._get_resource_subdirectory()
        possible_directories = (
            Path(skill_directory, "locale", self.language),
            Path(skill_directory, "locale", "en-us"),
            Path(skill_directory, resource_subdirectory, self.language),
            Path(skill_directory, resource_subdirectory, "en-us"),
            Path(skill_directory, resource_subdirectory),
        )
        for directory in possible_directories:
            if directory.exists():
                self.base_directory = directory
                if "en-us" in str(directory) and self.language != "en-us":
                    self.language = "en-us"
                break

    def _get_resource_subdirectory(self) -> str:
        """Returns the subdirectory for this resource type.

        In the older directory schemes, several resource types were stored
        in the same set of three directories (dialog, regex, vocab).
        """
        subdirectories = dict(
            dialog="dialog",
            entity="vocab",
            intent="vocab",
            list="dialog",
            named_value="dialog",
            regex="regex",
            template="dialog",
            vocab="vocab",
            word="dialog",
        )

        return subdirectories[self.resource_type]


class ResourceFile:
    """Loads a resource file for the user's configured language.

    Attributes:
        resource_type: attributes of the resource type (dialog, vocab, etc.)
        resource_name: file name of the resource, with or without extension
        file_path: absolute path to the file
    """

    def __init__(self, resource_type, resource_name):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.file_path = self._locate()

    def _locate(self):
        """Locates a resource file in the skill's locale directory.

        A skill's locale directory can contain a subdirectory structure defined
        by the skill author.  Walk the directory and any subdirectories to
        find the resource file.
        """
        file_path = None
        if self.resource_name.endswith(self.resource_type.file_extension):
            file_name = self.resource_name
        else:
            file_name = self.resource_name + self.resource_type.file_extension

        walk_directory = str(self.resource_type.base_directory)
        for directory, _, file_names in walk(walk_directory):
            if file_name in file_names:
                file_path = Path(directory, file_name)

        if file_path is None:
            sub_path = Path("text", self.resource_type.language, file_name)
            file_path = resolve_resource_file(str(sub_path))

        if file_path is None:
            LOG.error(f"Could not find resource file {file_name}")

        return file_path

    def load(self):
        """Override in subclass to define resource type loading behavior."""
        pass

    def _read(self) -> str:
        """Reads the specified file, removing comment and empty lines."""
        with open(self.file_path) as resource_file:
            for line in [line.strip() for line in resource_file.readlines()]:
                if not line or line.startswith("#"):
                    continue
                yield line


class DialogFile(ResourceFile):
    """Defines a dialog file, which is used instruct TTS what to speak."""

    def __init__(self, resource_type, resource_name):
        super().__init__(resource_type, resource_name)
        self.data = None

    def load(self) -> List[str]:
        """Load and lines from a file and populate the variables.

        Returns:
            Contents of the file with variables resolved.
        """
        dialogs = None
        if self.file_path is not None:
            dialogs = []
            for line in self._read():
                line = line.replace("{{", "{").replace("}}", "}")
                if self.data is not None:
                    line = line.format(**self.data)
                dialogs.append(line)

        return dialogs

    def render(self, dialog_renderer):
        """Renders a random phrase from a dialog file.

        If no file is found, the requested phrase is returned as the string. This
        will use the default language for translations.

        Returns:
            str: a randomized version of the phrase
        """
        return dialog_renderer.render(self.resource_name, self.data)


class VocabularyFile(ResourceFile):
    """Defines a vocabulary file, which skill use to form intents."""

    def load(self) -> List[List[str]]:
        """Loads a vocabulary file.

        If a record in a vocabulary file contains sets of words inside
        parentheses, generate a vocabulary item for each permutation within
        the parentheses.

        Returns:
            List of lines in the file.  Each item in the list is a list of
            strings that represent different options based on regular
            expression.
        """
        vocabulary = []
        if self.file_path is not None:
            for line in self._read():
                vocabulary.append(expand_options(line.lower()))

        return vocabulary


class NamedValueFile(ResourceFile):
    """Defines a named value file, which maps a variable to a values."""

    def __init__(self, resource_type, resource_name):
        super().__init__(resource_type, resource_name)
        self.delimiter = ","

    def load(self) -> dict:
        """Load file containing names and values.

        Returns:
            A dictionary representation of the records in the file.
        """
        named_values = dict()
        if self.file_path is not None:
            for line in self._read():
                name, value = self._load_line(line)
                if name is not None and value is not None:
                    named_values[name] = value

        return named_values

    def _load_line(self, line: str) -> Tuple[str, str]:
        """Attempts to split the name and value for dictionary loading.

        Args:
            line: a record in a .value file
        Returns:
            The name/value pair that will be loaded into a dictionary.
        """
        name = None
        value = None
        try:
            name, value = line.split(self.delimiter)
        except ValueError:
            LOG.exception(
                f"Failed to load value file {self.file_path} "
                f"record containing {line}"
            )

        return name, value


class ListFile(DialogFile):
    pass


class TemplateFile(DialogFile):
    pass


class RegexFile(ResourceFile):
    def load(self):
        regex_patterns = []
        if self.file_path:
            regex_patterns = [line for line in self._read()]

        return regex_patterns


class WordFile(ResourceFile):
    """Defines a word file, which defines a word in the configured language."""

    def load(self) -> Optional[str]:
        """Load and lines from a file and populate the variables.

        Returns:
            The word contained in the file
        """
        word = None
        if self.file_path is not None:
            for line in self._read():
                word = line
                break

        return word


class SkillResources:
    def __init__(self, skill_directory, language, dialog_renderer):
        self.skill_directory = skill_directory
        self.language = language
        self.types = self._define_resource_types()
        self.dialog_renderer = dialog_renderer
        self.static = dict()

    def _define_resource_types(self) -> SkillResourceTypes:
        """Defines all known types of skill resource files.

        A resource file contains information the skill needs to function.
        Examples include dialog files to be spoken and vocab files for intent
        matching.
        """
        resource_types = dict(
            dialog=ResourceType("dialog", ".dialog", self.language),
            entity=ResourceType("entity", ".entity", self.language),
            intent=ResourceType("intent", ".intent", self.language),
            list=ResourceType("list", ".list", self.language),
            named_value=ResourceType("named_value", ".value", self.language),
            regex=ResourceType("regex", ".rx", self.language),
            template=ResourceType("template", ".template", self.language),
            vocabulary=ResourceType("vocab", ".voc", self.language),
            word=ResourceType("word", ".word", self.language),
        )
        for resource_type in resource_types.values():
            resource_type.locate_base_directory(self.skill_directory)

        return SkillResourceTypes(**resource_types)

    def load_dialog_file(self, name, data=None) -> List[str]:
        """Loads the contents of a dialog file into memory.

        Named variables in the dialog are populated with values found in the
        data dictionary.

        Args:
            name: name of the dialog file (no extension needed)
            data: keyword arguments used to populate variables
        Returns:
            A list of phrases with variables resolved
        """
        dialog_file = DialogFile(self.types.dialog, name)
        dialog_file.data = data

        return dialog_file.load()

    def load_list_file(self, name, data=None) -> List[str]:
        """Load a file containing a list of words or phrases

        Named variables in the dialog are populated with values found in the
        data dictionary.

        Args:
            name: name of the list file (no extension needed)
            data: keyword arguments used to populate variables
        Returns:
            List of words or phrases read from the list file.
        """
        list_file = ListFile(self.types.list, name)
        list_file.data = data

        return list_file.load()

    def load_named_value_file(self, name, delimiter=None) -> dict:
        """Load file containing a set names and values.

        Loads a simple delimited file of name/value pairs.
        The name is the first item, the value is the second.

        Args:
            name: name of the .value file, no extension needed
            delimiter: delimiter character used
        Returns:
            File contents represented as a dictionary
        """
        if name in self.static:
            named_values = self.static[name]
        else:
            named_value_file = NamedValueFile(self.types.named_value, name)
            if delimiter is not None:
                named_value_file.delimiter = delimiter
            named_values = named_value_file.load()
            self.static[name] = named_values

        return named_values

    def load_regex_file(self, name) -> List[str]:
        """Loads a file containing regular expression patterns.

        The regular expression patterns are generally used to find a value
        in a user utterance the skill needs to properly perform the requested
        function.

        Args:
            name: name of the regular expression file, no extension needed
        Returns:
            List representation of the regular expression file.
        """
        regex_file = RegexFile(self.types.regex, name)

        return regex_file.load()

    def load_template_file(self, name, data=None) -> List[str]:
        """Loads the contents of a dialog file into memory.

        Named variables in the dialog are populated with values found in the
        data dictionary.

        Args:
            name: name of the dialog file (no extension needed)
            data: keyword arguments used to populate variables
        Returns:
            A list of phrases with variables resolved
        """
        template_file = TemplateFile(self.types.template, name)
        template_file.data = data

        return template_file.load()

    def load_vocabulary_file(self, name) -> List[List[str]]:
        """Loads a file containing variations of words meaning the same thing.

        A vocabulary file defines words a skill uses for intent matching.
        It can also be used to match words in an utterance after intent
        intent matching is complete.

        Args:
            name: name of the regular expression file, no extension needed
        Returns:
            List representation of the regular expression file.
        """
        vocabulary_file = VocabularyFile(self.types.vocabulary, name)

        return vocabulary_file.load()

    def load_word_file(self, name) -> Optional[str]:
        """Loads a file containing a word.

        Args:
            name: name of the regular expression file, no extension needed
        Returns:
            List representation of the regular expression file.
        """
        word_file = WordFile(self.types.word, name)

        return word_file.load()

    def render_dialog(self, name, data=None) -> str:
        """Selects a record from a dialog file at random for TTS purposes.

        Args:
            name: name of the list file (no extension needed)
            data: keyword arguments used to populate variables
        Returns:
            Random record from the file with variables resolved.
        """
        resource_file = DialogFile(self.types.dialog, name)
        resource_file.data = data

        return resource_file.render(self.dialog_renderer)

    def load_skill_vocabulary(self, alphanumeric_skill_id: str) -> dict:
        skill_vocabulary = {}
        base_directory = self.types.vocabulary.base_directory
        for directory, _, files in walk(base_directory):
            vocabulary_files = [
                file_name for file_name in files if file_name.endswith(".voc")
            ]
            for file_name in vocabulary_files:
                vocab_type = alphanumeric_skill_id + file_name[:-4].title()
                vocabulary = self.load_vocabulary_file(file_name)
                if vocabulary:
                    skill_vocabulary[vocab_type] = vocabulary

        return skill_vocabulary

    def load_skill_regex(self, alphanumeric_skill_id: str) -> List[str]:
        skill_regexes = []
        base_directory = self.types.regex.base_directory
        for directory, _, files in walk(base_directory):
            regex_files = [
                file_name for file_name in files if file_name.endswith(".rx")
            ]
            for file_name in regex_files:
                skill_regexes.extend(self.load_regex_file(file_name))

        skill_regexes = self._make_unique_regex_group(
            skill_regexes, alphanumeric_skill_id
        )

        return skill_regexes

    @staticmethod
    def _make_unique_regex_group(
        regexes: List[str], alphanumeric_skill_id: str
    ) -> List[str]:
        """Adds skill ID to group ID in a regular expression for uniqueness.

        Args:
            regexes: regex string
            alphanumeric_skill_id: skill identifier
        Returns:
            regular expressions with uniquely named group IDs
        Raises:
            re.error if the regex does not compile
        """
        modified_regexes = []
        for regex in regexes:
            base = "(?P<" + alphanumeric_skill_id
            modified_regex = base.join(regex.split("(?P<"))
            re.compile(modified_regex)
            modified_regexes.append(modified_regex)

        return modified_regexes


class RegexExtractor:
    """Extracts data from an utterance using regular expressions.

    Attributes:
        group_name:
        regex_patterns: regular expressions read from a .rx file
    """

    def __init__(self, group_name, regex_patterns):
        self.group_name = group_name
        self.regex_patterns = regex_patterns

    def extract(self, utterance) -> Optional[str]:
        """Attempt to find a value in a user request.

        Args:
            utterance: request spoken by the user

        Returns:
            The value extracted from the utterance, if found
        """
        extract = None
        pattern_match = self._match_utterance_to_patterns(utterance)
        if pattern_match is not None:
            extract = self._extract_group_from_match(pattern_match)
        self._log_extraction_result(extract)

        return extract

    def _match_utterance_to_patterns(self, utterance: str):
        """Match regular expressions to user request.

        Args:
            utterance: request spoken by the user

        Returns:
            a regular expression match object if a match is found
        """
        pattern_match = None
        for pattern in self.regex_patterns:
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
        else:
            if not extract:
                extract = None

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

    # Munge excluded keywords
    excludes = []
    for i in intent_parser.excludes:
        if not i.startswith(skill_id):
            kw = skill_id + i
            excludes.append(kw)
        else:
            excludes.append(i)
    intent_parser.excludes = excludes
