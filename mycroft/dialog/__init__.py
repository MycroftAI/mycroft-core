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
import random
import os
import re
from pathlib import Path
from os.path import join

from mycroft.util import resolve_resource_file
from mycroft.util.log import LOG


__doc__ = """

"""


class MustacheDialogRenderer:
    """
    A dialog template renderer based on the mustache templating language.
    """

    def __init__(self):
        self.templates = {}

    def load_template_file(self, template_name, filename):
        """
        Load a template by file name into the templates cache.

        Args:
            template_name (str): a unique identifier for a group of templates
            filename (str): a fully qualified filename of a mustache template.
        """
        with open(filename, 'r', encoding='utf8') as f:
            for line in f:
                template_text = line.strip()
                # Skip all lines starting with '#' and all empty lines
                if (not template_text.startswith('#') and
                        template_text != ''):
                    if template_name not in self.templates:
                        self.templates[template_name] = []

                    # convert to standard python format string syntax. From
                    # double (or more) '{' followed by any number of
                    # whitespace followed by actual key followed by any number
                    # of whitespace followed by double (or more) '}'
                    template_text = re.sub(r'\{\{+\s*(.*?)\s*\}\}+', r'{\1}',
                                           template_text)

                    self.templates[template_name].append(template_text)

    def render(self, template_name, context=None, index=None):
        """
        Given a template name, pick a template and render it using the context.
        If no matching template exists use template_name as template.

        Args:
            template_name (str): the name of a template group.
            context (dict): dictionary representing values to be rendered
            index (int): optional, the specific index in the collection of
                templates

        Returns:
            str: the rendered string
        """
        context = context or {}
        if template_name not in self.templates:
            # When not found, return the name itself as the dialog
            # This allows things like render("record.not.found") to either
            # find a translation file "record.not.found.dialog" or return
            # "record not found" literal.
            return template_name.replace(".", " ")

        template_functions = self.templates.get(template_name)
        if index is None:
            line = random.choice(template_functions)
        else:
            line = template_functions[index % len(template_functions)]
        # Replace {key} in line with matching values from context
        line = line.format(**context)
        return line


class DialogLoader:
    """
    Loads a collection of dialog files into a renderer implementation.
    """

    def __init__(self, renderer_factory=MustacheDialogRenderer):
        self.__renderer = renderer_factory()

    def load(self, dialog_dir):
        """
        Load all dialog files within the specified directory.

        Args:
            dialog_dir (str): directory that contains dialog files

        Returns:
            a loaded instance of a dialog renderer
        """
        directory = Path(dialog_dir)
        if not directory.exists() or not directory.is_dir():
            LOG.warning("No dialog files found: {}".format(dialog_dir))
            return self.__renderer

        for path, _, files in os.walk(str(directory)):
            for f in files:
                if f.endswith(".dialog"):
                    self.__renderer.load_template_file(
                        f.replace('.dialog', ''),
                        join(path, f))
        return self.__renderer


def get(phrase, lang=None, context=None):
    """
    Looks up a resource file for the given phrase.  If no file
    is found, the requested phrase is returned as the string.
    This will use the default language for translations.

    Args:
        phrase (str): resource phrase to retrieve/translate
        lang (str): the language to use
        context (dict): values to be inserted into the string

    Returns:
        str: a randomized and/or translated version of the phrase
    """

    if not lang:
        from mycroft.configuration import Configuration
        lang = Configuration.get().get("lang")

    filename = "text/" + lang.lower() + "/" + phrase + ".dialog"
    template = resolve_resource_file(filename)
    if not template:
        LOG.debug("Resource file not found: {}".format(filename))
        return phrase

    stache = MustacheDialogRenderer()
    stache.load_template_file("template", template)
    if not context:
        context = {}
    return stache.render("template", context)
