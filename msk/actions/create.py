# Copyright (c) 2018 Mycroft AI, Inc.
#
# This file is part of Mycroft Skills Kit
# (see https://github.com/MycroftAI/mycroft-skills-kit).
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
import atexit

import re
from argparse import ArgumentParser
import requests
from git import Git, GitCommandError
from github import GithubException
from github.Repository import Repository
from os import makedirs
from os.path import join, exists, isdir, basename, splitext
import shutil
from shutil import rmtree
from subprocess import call
from typing import Callable, Optional
from colorama import Style, Fore, init as colorama_init

from msk.console_action import ConsoleAction
from msk.exceptions import GithubRepoExists, UnrelatedGithubHistory
from msk.lazy import Lazy
from msk.util import ask_input, to_camel, ask_yes_no, ask_input_lines, \
    print_error, get_licenses, ask_choice

readme_template = '''# <img src="https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/{icon}.svg" card_color="{color}" width="50" height="50" style="vertical-align:bottom"/> \
{title_name}
{short_description}

## About
{long_description}

## Examples
{examples}
{credits}
## Category
**{category_primary}**
{categories_other}
## Tags
{tags}
'''

credits_template = '''## Credits
{author}
'''

init_template = '''from mycroft import MycroftSkill, intent_file_handler


class {class_name}(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('{intent_name}.intent')
    def handle_{handler_name}(self, message):
{handler_code}


def create_skill():
    return {class_name}()

'''

gitignore_template = '''__pycache__/
*.qmlc
settings.json

'''

settingsmeta_template = '''
skillMetadata:
  sections:
    - name: Options << Name of section
      fields:
        - name: internal_python_variable_name
          type: text
          label: Setting Friendly Display Name
          value: ""
          placeholder: demo prompt in the input box
    - name: Login << Name of another section
      fields:
        - type: label
          label: Just a little bit of extra info for the user to understand following settings
        - name: username
          type: text
          label: Username
          value: ""
        - name: password
          type: password
          label: Password
          value: ""
'''

manifest_template = """
# This file details all external dependencies required by your skill. If your skill does
# not require any dependencies, please delete this file before submitting a pull request.
#
# To use this file, uncomment the lines you need, and fill in the appropriate information.
#
# dependencies:
#   # Pip dependencies on PyPI
#   python:
#     - requests
#     - gensim
#
#   # Install packages with the system package manager
#   # This searches for the provided executable and uses the package names
#   system:
#     # For simple packages, this is all that is necessary
#     all: pianobar piano-dev
#
#     # If the package has a certain name on a different platform:
#     pkcon: pianobar libpiano-dev  # For the mycroft platform
#     apt-get: pianobar libpiano-dev  # For Ubuntu/Debian
#
#   # Require certain executables to be in the PATH for the install to succeed
#   exes:
#     - pianobar
#
#   # Require the installation of other skills before installing this skill
#   skill:
#     - my-other-skill
"""


def pretty_license(path):
    pretty = basename(path)
    pretty = splitext(pretty)[0]
    pretty = pretty.replace('-', ' ')
    return pretty


class CreateAction(ConsoleAction):
    def __init__(self, args, name: str = None):
        colorama_init()
        if name:
            self.name = name

    @staticmethod
    def register(parser: ArgumentParser):
        pass

    @Lazy
    def name(self) -> str:
        name_to_skill = {skill.name: skill for skill in self.msm.list()}
        while True:
            name = ask_input(
                'Enter a short unique skill name (ie. "siren alarm" or "pizza orderer"):',
                lambda x: re.match(r'^[a-zA-Z \-]+$', x), 'Please use only letter and spaces.'
            ).strip(' -').lower().replace(' ', '-')
            skill = name_to_skill.get(name, name_to_skill.get('{}-skill'.format(name)))
            if skill:
                print('The skill {} {}already exists'.format(
                    skill.name, 'by {} '.format(skill.author) * bool(skill.author)
                ))
                if ask_yes_no('Remove it? (y/N)', False):
                    rmtree(skill.path)
                else:
                    continue
            class_name = '{}Skill'.format(to_camel(name.replace('-', '_')))
            repo_name = '{}-skill'.format(name)
            print()
            print('Class name:', class_name)
            print('Repo name:', repo_name)
            print()
            alright = ask_yes_no('Looks good? (Y/n)', True)
            if alright:
                return name

    path = Lazy(lambda s: join(s.msm.skills_dir, s.name + '-skill'))
    git = Lazy(lambda s: Git(s.path))
    short_description = Lazy(lambda s: ask_input(
        'Enter a one line description for your skill (ie. Orders fresh pizzas from the store):\n-',
    ).capitalize())
    author = Lazy(lambda s: ask_input('Enter author:'))
    intent_lines = Lazy(lambda s: [
        i.capitalize() for i in ask_input_lines(
            'Enter some example phrases to trigger your skill:', '-'
        )
    ])
    dialog_lines = Lazy(lambda s: [
        i.capitalize() for i in ask_input_lines(
            'Enter what your skill should say to respond:', '-'
        )
    ])
    intent_entities = Lazy(lambda s: set(re.findall(
        r'(?<={)[a-z_A-Z]*(?=})', '\n'.join(i for i in s.intent_lines)
    )))
    dialog_entities = Lazy(lambda s: set(re.findall(
        r'(?<={)[a-z_A-Z]*(?=})', '\n'.join(s.dialog_lines)
    )))
    long_description = Lazy(lambda s: '\n\n'.join(
        ask_input_lines('Enter a long description:', '>')
    ).strip().capitalize())
    icon = Lazy(lambda s: ask_input(
        'Go to Font Awesome ({blue}fontawesome.com/cheatsheet{reset}) and choose an icon.'
        '\nEnter the name of the icon (default: robot):'.format(blue=Fore.BLUE + Style.BRIGHT, reset=Style.RESET_ALL),
        validator=lambda x:
        x == '' or requests.get("https://raw.githack.com/FortAwesome/Font-Awesome/"
                                "master/svgs/solid/{x}.svg".format(x=x)).ok,
        on_fail="\n\n{red}Error: The name was not found. Make sure you spelled the icon name right,"
                " and try again.{reset}\n".format(red=Fore.RED + Style.BRIGHT, reset=Style.RESET_ALL)))
    color = Lazy(lambda s: ask_input(
        "Pick a {yellow}color{reset} for your icon. Find a color that matches the color scheme at"
        " {blue}mycroft.ai/colors{reset}, or pick a color at: {blue}color-hex.com.{reset}"
        "\nEnter the color hex code including the # (default: #22A7F0):".format(blue=Fore.BLUE + Style.BRIGHT, yellow=Fore.YELLOW, reset=Style.RESET_ALL),
        validator=lambda hex_code: 
        hex_code == '' or hex_code[0] == "#" and len(hex_code) in [4, 7],
        on_fail="\n{red}Check that you entered a correct hex code, and try again.{reset}\n".format(
            red=Fore.RED + Style.BRIGHT,
            reset=Style.RESET_ALL)
    ))

    category_options = ['Daily', 'Configuration', 'Entertainment', 'Information', 'IoT',
                        'Music & Audio', 'Media', 'Productivity', 'Transport']
    category_primary = Lazy(lambda s: s.ask_category_primary())
    categories_other= Lazy(lambda s: s.ask_categories_other(s.category_primary))
    
    tags = Lazy(lambda s: [
        i.capitalize() for i in ask_input_lines(
            'Enter tags to make it easier to search for your skill (optional):',
            '-'
        )
    ])

    manifest = Lazy(lambda s: manifest_template if ask_yes_no(message="Does this Skill depend on Python Packages (PyPI), System Packages (apt-get/others), or other skills?"
                                                            "\nThis will create a manifest.yml file for you to define the dependencies for your Skill."
                                                             "\nCheck the Mycroft documentation at mycroft.ai/to/skill-dependencies to learn more about including dependencies, and the manifest.yml file, in Skills. (y/N)", default=False) else None)

    readme = Lazy(lambda s: readme_template.format(
        title_name=s.name.replace('-', ' ').title(),
        short_description=s.short_description,
        long_description=s.long_description,
        examples=''.join('* "{}"\n'.format(i) for i in s.intent_lines),
        credits=credits_template.format(author=s.author),
        icon=s.icon or 'robot',
        color=s.color.upper() or '#22A7F0',
        category_primary=s.category_primary,
        categories_other=''.join('{}\n'.format(i) for i in s.categories_other),
        tags=''.join('#{}\n'.format(i) for i in s.tags),
    ))
    init_file = Lazy(lambda s: init_template.format(
        class_name=to_camel(s.name.replace('-', '_')),
        handler_name=s.intent_name.replace('.', '_'),
        handler_code='\n'.join(
            ' ' * 8 * bool(i) + i
            for i in [
                "{ent} = message.data.get('{ent}')".format(ent=entity)
                for entity in sorted(s.intent_entities)
            ] + [
                "{ent} = ''".format(ent=entity)
                for entity in sorted(s.dialog_entities - s.intent_entities)
            ] + [''] * bool(
                s.dialog_entities | s.intent_entities
            ) + "self.speak_dialog('{intent}'{args})".format(
                intent=s.intent_name, args=", data={{\n{}\n}}".format(',\n'.join(
                    "    '{ent}': {ent}".format(ent=entity)
                    for entity in s.dialog_entities | s.intent_entities
                )) * bool(s.dialog_entities | s.intent_entities)
            ).split('\n')
        ),
        intent_name=s.intent_name
    ))

    intent_name = Lazy(lambda s: '.'.join(reversed(s.name.split('-'))))

    def add_locale(self):
        makedirs(join(self.path, 'locale', self.lang))
        with open(join(self.path, 'locale', self.lang, self.intent_name + '.intent'), 'w') as f:
            f.write('\n'.join(self.intent_lines + ['']))
        with open(join(self.path, 'locale', self.lang, self.intent_name + '.dialog'), 'w') as f:
            f.write('\n'.join(self.dialog_lines + ['']))

    def ask_category_primary(self):
        """Ask user to select primary category."""
        category = ask_choice('\nCategories define where the skill will display in the Marketplace. \nEnter the primary category for your skill: ',
                                    self.category_options, allow_empty=False)
        return category

    def ask_categories_other(self, category_primary):
        """Ask user to select aditional categories."""
        categories_other = []
        while True:
            category_options_formatted = []
            for category in self.category_options:
                if (category == category_primary) or (category in categories_other):
                    category = '*' + category + '*'
                category_options_formatted.append(category)
            category = ask_choice('Enter additional categories (optional):',
                                  category_options_formatted, allow_empty=True,
                                  on_empty=None)
            if (category != None) and (category[0] != '*'):
                categories_other.append(category)
            if category == None:
                break
        return categories_other

    def license(self):
        """Ask user to select a license for the repo."""
        license_files = get_licenses()
        print('For uploading a skill a license is required.\n'
              'Choose one of the licenses listed below or add one later.\n')
        for num, pth in zip(range(1, 1 + len(license_files)), license_files):
            print('{}: {}'.format(num, pretty_license(pth)))
        choice = ask_input('Choose license above or press Enter to skip?')
        if choice.isdigit():
            index = int(choice) - 1
            shutil.copy(license_files[index], join(self.path, 'LICENSE.md'))
            print('\nSome of these require that you insert the project name '
                  'and/or author\'s name. Please check the license file and '
                  'add the appropriate information.\n')

    def initialize_template(self, files: set = None):
        git = Git(self.path)

        skill_template = [
            ('', lambda: makedirs(self.path)),
            ('locale', self.add_locale),
            ('__init__.py', lambda: self.init_file),
            ('README.md', lambda: self.readme),
            ('LICENSE.md', self.license),
            ('.gitignore', lambda: gitignore_template),
            ('settingsmeta.yaml', lambda: settingsmeta_template.format(
                capital_desc=self.name.replace('-', ' ').capitalize()
            )),
            ('manifest.yml', lambda: self.manifest),
            ('.git', lambda: git.init())
        ]


        def cleanup():
            rmtree(self.path)

        if not isdir(self.path):
            atexit.register(cleanup)
        for file, handler in skill_template:
            if files and file not in files:
                continue
            if not exists(join(self.path, file)):
                result = handler()
                if isinstance(result, str) and not exists(join(self.path, file)):
                    with open(join(self.path, file), 'w') as f:
                        f.write(result)
        atexit.unregister(cleanup)

    def commit_changes(self):
        if self.git.rev_parse('HEAD', with_exceptions=False) == 'HEAD':
            self.git.add('.')
            self.git.commit(message='Initial commit')

    def force_push(self, get_repo_name: Callable = None) -> Optional[Repository]:
        if ask_yes_no(
                'Are you sure you want to overwrite the remote github repo? '
                'This cannot be undone and you will lose your commit '
                'history! (y/N)',
                False):
            repo_name = (get_repo_name and get_repo_name()) or (
                    self.name + '-skill')
            repo = self.user.get_repo(repo_name)
            self.git.push('origin', 'master', force=True)
            print('Force pushed to GitHub repo:', repo.html_url)
            return repo

    def link_github_repo(self, get_repo_name: Callable = None) -> Optional[Repository]:
        if 'origin' not in Git(self.path).remote().split('\n'):
            if ask_yes_no(
                    'Would you like to link an existing GitHub repo to it? (Y/n)',
                    True):
                repo_name = (get_repo_name and get_repo_name()) or (
                        self.name + '-skill')
                repo = self.user.get_repo(repo_name)
                self.git.remote('add', 'origin', repo.html_url)
                self.git.fetch()
                try:
                    self.git.pull('origin', 'master')
                except GitCommandError as e:
                    if e.status == 128:
                        raise UnrelatedGithubHistory(repo_name) from e
                    raise
                self.git.push('origin', 'master', set_upstream=True)
                print('Linked and pushed to GitHub repo:', repo.html_url)
                return repo

    def create_github_repo(self, get_repo_name: Callable = None) -> Optional[Repository]:
        if 'origin' not in Git(self.path).remote().split('\n'):
            if ask_yes_no('Would you like to create a GitHub repo for it? (Y/n)', True):
                repo_name = (get_repo_name and get_repo_name()) or (self.name + '-skill')
                try:
                    repo = self.user.create_repo(repo_name, self.short_description)
                except GithubException as e:
                    if e.status == 422:
                        raise GithubRepoExists(repo_name) from e
                    raise
                self.git.remote('add', 'origin', repo.html_url)
                call(['git', 'push', '-u', 'origin', 'master'], cwd=self.git.working_dir)
                print('Created GitHub repo:', repo.html_url)
                return repo
        return None

    def perform(self):
        self.initialize_template()
        self.commit_changes()
        with print_error(GithubRepoExists):
            self.create_github_repo()
        print('Created skill at:', self.path)
