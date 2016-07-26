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
from mycroft.util import log

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

        :param template_name: a unique identifier for a group of templates.

        :param filename: a fully qualified filename of a mustache template.

        :return:
        """
        with open(filename, 'r') as f:
            for line in f:
                template_text = line.strip()
                if template_name not in self.templates:
                    self.templates[template_name] = []

                self.templates[template_name].append(template_text)

    def render(self, template_name, context={}, index=None):
        """
        Given a template name, pick a template and render it with the provided
        context.

        :param template_name: the name of a template group.

        :param context: dictionary representing values to be rendered

        :param index: optional, the specific index in the collection of
            templates

        :raises NotImplementedError: if no template can be found identified by
            template_name

        :return:
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

        :param dialog_dir: directory that contains dialog files

        :return: a loaded instance of a dialog renderer
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
