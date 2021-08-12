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
#
# Mycroft documentation build configuration file
#
import sys
import re
import os
from os.path import dirname, join

import sphinx_rtd_theme
from sphinx.ext.autodoc import (
    ClassLevelDocumenter, InstanceAttributeDocumenter)


def iad_add_directive_header(self, sig):
    ClassLevelDocumenter.add_directive_header(self, sig)


InstanceAttributeDocumenter.add_directive_header = iad_add_directive_header

sys.path.insert(0, os.path.abspath('../'))

# General Configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon'
]
req_path = os.path.join(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))), 'requirements', 'requirements.txt')

# To easily run sphinx without additional installation autodoc_mock_imports
# sets modules to mock.

# Step 1: Pull module names to mock from requirements
# Assuming package name is the same as the module name
with open(req_path) as f:
    autodoc_mock_imports = map(str.strip, re.findall(r'^\s*[a-zA-Z_]*',
                               f.read().lower().replace('-', '_'),
                               flags=re.MULTILINE))

# Step 2: Add custom names
# Not all module names match the package name (as stated in requirements.txt)
# this adds the modules whose names don't match the package name.
autodoc_mock_imports = list(autodoc_mock_imports) + [
    'adapt',
    'alsaaudio',
    'dateutil',
    'past',
    'serial',
    'websocket',
    'speech_recognition',
    'yaml',
    'mycroft_bus_client'
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'


def get_version():
    version_file = join(dirname(__file__),
                        '..', 'mycroft', 'version', '__init__.py')
    with open(version_file) as f:
        while 'START_VERSION_BLOCK' not in f.readline():
            pass

        def safe_read_version_line():
            try:
                return f.readline().split('=')[1].strip()
            except Exception:
                return '0'

        major = safe_read_version_line()
        minor = safe_read_version_line()
        build = safe_read_version_line()
        return 'v' + '.'.join((major, minor, build))


# General Info
project = 'Mycroft'
copyright = '2017, Mycroft AI Inc.'
author = 'Mycroft AI Inc.'

version = get_version()
release = version

language = None
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Syntax Highlighting
pygments_style = 'sphinx'

todo_include_todos = False

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
html_theme_options = {
    'navigation_depth': 4,
}

html_static_path = []
htmlhelp_basename = 'Mycroftdoc'

# Options for LaTeX output

latex_elements = {}
latex_documents = [
    (master_doc, 'Mycroft.tex', 'Mycroft Documentation',
     'Matthew Scholefield', 'manual'),
]


# Options for manual page output

man_pages = [
    (master_doc, 'mycroft', 'Mycroft Documentation',
     [author], 1)
]


# Options for Texinfo output

texinfo_documents = [
    (master_doc, 'Mycroft', 'Mycroft Documentation',
     author, 'Mycroft', 'Mycroft Artificial Intelligence Platform.',
     'Miscellaneous'),
]

# Options for Napoleon

napoleon_google_docstring = True
napoleon_numpy_docstring = False
