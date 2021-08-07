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

import os
from configparser import NoOptionError
from contextlib import contextmanager
from difflib import SequenceMatcher
from functools import wraps
from git.config import GitConfigParser, get_config_path
from github import Github, GithubException
from github.Repository import Repository
from msm import SkillEntry
from os import chmod
from os.path import join, dirname
from tempfile import mkstemp
from typing import Optional
from glob import glob
from pathlib import Path

from msk import __version__
from msk.exceptions import PRModified, MskException, SkillNameTaken

ASKPASS = '''#!/usr/bin/env python3
import sys
print(r"""{token}"""
)'''

skills_kit_footer = '<sub>Created with [mycroft-skills-kit]({}) v{}</sub>' \
                    .format('https://github.com/mycroftai/mycroft-skills-kit',
                            __version__)

tokendir = str(Path.home()) + '/.mycroft/msk/'
tokenfile = tokendir + 'GITHUB_TOKEN'


def register_git_injector(token):
    """Generate a script that writes the token to the git command line tool"""
    fd, tmp_path = mkstemp()
    atexit.register(lambda: os.remove(tmp_path))

    with os.fdopen(fd, 'w') as f:
        f.write(ASKPASS.format(
            token=token.replace('"""', r'\"\"\"')
        ))

    chmod(tmp_path, 0o700)
    os.environ['GIT_ASKPASS'] = tmp_path


def ask_for_github_token() -> Github:
    """Ask for GitHub Token if there isnt stored token
       or stored token is invalid"""
    print('')
    token = get_stored_github_token()
    if token and check_token(token):
        github = Github(token)
        register_git_injector(token)
        return github
    else:
        retry = False
        while True:
            if not retry:
                print('To authenticate with GitHub a Personal Access Token is needed.')
                print('    1. Go to https://github.com/settings/tokens/new create one')
                print('    2. Give the token a name like mycroft-msk')
                print('    3. Select the scopes')
                print('       [X] repo')
                print('    4. Click Generate Token (at bottom of page)')
                print('    5. Copy the generated token')
                print('    6. Paste it in below')
                print('')
                retry = True
            token = input('Personal Access Token: ')
            if check_token(token):
                github = Github(token)
                store_github_token(token)
                register_git_injector(token)
                return github
            else:
                print('')
                print('Token is incorrect.')
                print('The reason for this can be that token is missing repo scope')
                print('or the token is invalid.')
                print('Please retry.')
                print('')


def check_token(token):
    """Check if at GitHub Token has 'repo' in the scope"""
    github = Github(token)
    try:
        _ = github.get_user().login
        _ = github.oauth_scopes
        if 'repo' in github.oauth_scopes:
            return True
        else:
            return False
    except Exception:
        return False


def get_stored_github_token():
    """Returns stored GitHub token or false if there isnt
       one or the token is invalid"""
    if os.path.isfile(tokenfile):
        with open(tokenfile, 'r') as f:
            token = f.readline()
        if not check_token(token):
            os.remove(tokenfile)
        else:
            return(token)
    else:
        return False


def store_github_token(token):
    """Ask if user will store GitHUb token and if yes store"""
    print('')
    if ask_yes_no('Do you want msk to store the GitHub Personal Access Token? (Y/n)', True):
        if not os.path.exists(tokendir):
            os.makedirs(tokendir)
        with open(tokenfile, 'w') as f:
            f.write(token)
            os.chmod(tokenfile, 0o600)
        print('Your GitHub Personal Access Token is stored in ' + tokenfile)
        print('')
    else:
        print('Remember to store your token in a safe place.')
        print('')


def skill_repo_name(url: str):
    return '{}/{}'.format(SkillEntry.extract_author(url),
                          SkillEntry.extract_repo_name(url))


def ask_input(message: str, validator=lambda x: True, on_fail='Invalid entry'):
    while True:
        resp = input(message + ' ').strip()
        try:
            if validator(resp):
                return resp
        except Exception:
            pass
        o = on_fail(resp) if callable(on_fail) else on_fail
        if isinstance(o, str):
            print(o)


def ask_choice(message: str, choices: list,
               allow_empty=False, on_empty=None) -> Optional[str]:
    if not choices:
        if allow_empty:
            print(on_empty)
            return None
        else:
            raise MskException(on_empty or 'Error with "{}"'.format(message))

    print()
    print(message)
    print('\n'.join(
        '{}. {}'.format(i + 1, choice)
        for i, choice in enumerate(choices)
    ))
    print()

    def find_match(x):
        if not x and allow_empty:
            return ...
        try:
            return choices[int(x) - 1]
        except (ValueError, IndexError):
            pass

        def calc_conf(y):
            return SequenceMatcher(a=x, b=y).ratio()
        best_choice = max(choices, key=calc_conf)
        best_conf = calc_conf(best_choice)
        if best_conf > 0.8:
            return best_choice
        raise ValueError

    resp = find_match(ask_input(
        '>', find_match, 'Please enter one of the options.'
    ))
    return None if resp is ... else resp


def ask_input_lines(message: str, bullet: str = '>') -> list:
    print(message)
    lines = []
    while len(lines) < 1 or lines[-1]:
        lines.append(ask_input(bullet))
    return lines[:-1]


def ask_yes_no(message: str, default: Optional[bool]) -> bool:
    resp = ask_input(message,
                     lambda x: (not x and default is not None) or x in 'yYnN')
    return {'n': False, 'y': True, '': default}[resp.lower()]


def create_or_edit_pr(title: str, body: str, skills_repo: Repository,
                      user, branch: str, repo_branch: str):
    base = repo_branch
    head = '{}:{}'.format(user.login, branch)
    pulls = list(skills_repo.get_pulls(base=base, head=head))
    if pulls:
        pull = pulls[0]
        if 'mycroft-skills-kit' in pull.body:
            pull.edit(title, body)
        else:
            raise PRModified('Not updating description since it was not autogenerated')
        return pull
    else:
        try:
            return skills_repo.create_pull(title, body, base=base, head=head)
        except GithubException as e:
            if e.status == 422:
                raise SkillNameTaken(title) from e
            raise


def to_camel(snake):
    """time_skill -> TimeSkill"""
    return snake.title().replace('_', '')


def to_snake(camel):
    """TimeSkill -> time_skill"""
    if not camel:
        return camel
    return ''.join('_' + x if 'A' <= x <= 'Z' else x for x in camel) \
           .lower()[camel[0].isupper():]


@contextmanager
def print_error(exception):
    try:
        yield
    except exception as e:
        print('{}: {}'.format(exception.__name__, e))


def read_file(*path):
    with open(join(*path)) as f:
        return f.read()


def read_lines(*path):
    with open(join(*path)) as f:
        return [i for i in (i.strip() for i in f.readlines()) if i]


def serialized(func):
    """Write a serializer by yielding each line of output"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return '\n'.join(
            ' '.join(parts) if isinstance(parts, tuple) else parts
            for parts in func(*args, **kwargs)
        )

    return wrapper


def get_licenses():
    licenses = glob(join(dirname(__file__), 'licenses', '*.txt'))
    licenses.sort()
    return licenses


GIT_IDENTITY_INFO = '''=== Git Identity ===
msk uses Git to save skills to Github and when submitting a skill to the
Mycroft Marketplace. To use Git, Git needs to know your Name and
E-mail address. This is important because every Git commit uses the
information to show the responsible party for the submission.
'''


GIT_MANUAL_CHANGE_INFO = '''
Thank you. :)

If you need to change this in the future use

    git --config user.name "My Name"

and

    git --config user.email "me@myhost.com"

'''


def ensure_git_user():
    """Prompt for fullname and email if git config is missing it."""
    conf_path = get_config_path('global')
    with GitConfigParser(conf_path, read_only=False) as conf_parser:

        # Make sure a user section exists
        if 'user' not in conf_parser.sections():
            conf_parser.add_section('user')

        # Check for missing options using the ConfigParser and insert them
        # if they're missing.
        name, email = (None, None)
        try:
            name = conf_parser.get(section='user', option='name')
        except NoOptionError:
            pass  # Name doesn't exist deal with it later
        try:
            email = conf_parser.get(section='user', option='email')
        except NoOptionError:
            pass  # E-mail doesn't exist, deal with it later

        if not all((name, email)):
            # Some of the needed config is missing
            print(GIT_IDENTITY_INFO)
            if not name:
                name = input('Please enter Full name: ')
                conf_parser.set('user', 'name', name)
            if not email:
                email = input('Please enter e-mail address: ')
                conf_parser.set('user', 'email', email)

            print(GIT_MANUAL_CHANGE_INFO)
