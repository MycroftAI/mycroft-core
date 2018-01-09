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
from io import open

import os
import re

from mycroft.util import resolve_resource_file
from mycroft.util.log import LOG


__doc__ = """

"""


class MustacheDialogRenderer(object):
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
        with open(filename, 'r') as f:
            for line in f:
                template_text = line.strip()
                if template_name not in self.templates:
                    self.templates[template_name] = []

                # convert to standard python format string syntax. From
                # double (or more) '{' followed by any number of whitespace
                # followed by actual key followed by any number of whitespace
                # followed by double (or more) '}'
                template_text = re.sub('\{\{+\s*(.*?)\s*\}\}+', r'{\1}',
                                       template_text)

                self.templates[template_name].append(template_text)

    def render(self, template_name, context=None, index=None):
        """
        Given a template name, pick a template and render it using the context

        Args:
            template_name (str): the name of a template group.
            context (dict): dictionary representing values to be rendered
            index (int): optional, the specific index in the collection of
                templates

        Returns:
            str: the rendered string

        Raises:
            NotImplementedError: if no template can be found identified by
                template_name
        """
        context = context or {}
        if template_name not in self.templates:
            raise NotImplementedError("Template not found: %s" % template_name)
        template_functions = self.templates.get(template_name)
        if index is None:
            index = random.randrange(len(template_functions))
        else:
            index %= len(template_functions)
        line = template_functions[index]
        line = line.format(**context)
        return line


class DialogLoader(object):
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
        if not os.path.exists(dialog_dir) or not os.path.isdir(dialog_dir):
            LOG.warning("No dialog found: " + dialog_dir)
            return self.__renderer

        for f in sorted(
                filter(lambda x: os.path.isfile(
                    os.path.join(dialog_dir, x)), os.listdir(dialog_dir))):
            dialog_entry_name = os.path.splitext(f)[0]
            self.__renderer.load_template_file(
                dialog_entry_name, os.path.join(dialog_dir, f))

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
        LOG.debug("Resource file not found: " + filename)
        return phrase

    stache = MustacheDialogRenderer()
    stache.load_template_file("template", template)
    if not context:
        context = {}
    return stache.render("template", context)
