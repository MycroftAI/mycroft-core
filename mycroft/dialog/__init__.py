# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import pystache
import os
import random
from mycroft.util import log, resolve_resource_file

__author__ = 'seanfitz'
logger = log.getLogger(__name__)

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

                self.templates[template_name].append(template_text)

    def render(self, template_name, context={}, index=None):
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
        if template_name not in self.templates:
            raise NotImplementedError("Template not found: %s" % template_name)
        template_functions = self.templates.get(template_name)
        if index is None:
            index = random.randrange(len(template_functions))
        else:
            index %= len(template_functions)
        return pystache.render(template_functions[index], context)


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
            logger.warn("No dialog found: " + dialog_dir)
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
        from mycroft.configuration import ConfigurationManager
        lang = ConfigurationManager.instance().get("lang")

    filename = "text/"+lang.lower()+"/"+phrase+".dialog"
    template = resolve_resource_file(filename)
    if not template:
        logger.debug("Resource file not found: " + filename)
        return phrase

    stache = MustacheDialogRenderer()
    stache.load_template_file("template", template)
    if not context:
        context = {}
    return stache.render("template", context)
