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
import os
import shutil
from argparse import ArgumentParser
from git import Git, GitCommandError
from msm import SkillEntry
from os import listdir
from os.path import join, abspath, expanduser, basename

from msk.actions.create import CreateAction
from msk.console_action import ConsoleAction
from msk.exceptions import MskException, NoGitRepository, \
    UnrelatedGithubHistory, GithubRepoExists
from msk.lazy import Lazy
from msk.repo_action import SkillData
from msk.util import skills_kit_footer, \
    create_or_edit_pr, ask_yes_no, skill_repo_name, read_file, ask_choice

body_template = '''
## Info

This PR adds the new skill, [{skill_name}]({skill_url}), to the skills repo.

## Description

{description}

''' + skills_kit_footer


def exists_in_remote(git, repo_path):
    """Checks if the file at repo_path exists in remote HEAD."""
    try:
        remote_info = git.remote('show', 'origin').split('\n')
        heads = [e.split(':')[1].strip() for e in remote_info if 'HEAD' in e]
        remote_file = 'origin/{}:{}'.format(heads[0], repo_path)
        git.cat_file(remote_file, e=True)
    except GitCommandError:
        return False
    else:
        return True


class UploadAction(ConsoleAction):
    def __init__(self, args):
        folder = abspath(expanduser(args.skill_folder))
        self.entry = SkillEntry.from_folder(folder)
        skills_dir = abspath(expanduser(self.msm.skills_dir))
        if join(skills_dir, basename(folder)) != folder:
            raise MskException('Skill folder, {}, not directly within skills directory, {}.'.format(
                args.skill_folder, self.msm.skills_dir
            ))
        self.skill_dir = folder

    git = Lazy(lambda s: Git(s.entry.path))  # type: Git

    @staticmethod
    def register(parser: ArgumentParser):
        pass  # Implemented in SubmitAction

    def check_valid(self):
        """Check that the skill contains all required files before uploading.
        """
        results = []
        if not (exists_in_remote(self.git, 'LICENSE.md') or
                exists_in_remote(self.git, 'LICENSE') or
                exists_in_remote(self.git, 'LICENSE.txt')):
            print('To have your Skill available for installation through the '
                  'Skills Marketplace, a license is required.\n'
                  'Please select one and add it to the skill as '
                  '`LICENSE.md.`\n'
                  'See https://opensource.org/licenses for information on '
                  'open source license options.')
            results.append(False)
        else:
            results.append(True)

        if not exists_in_remote(self.git, 'README.md'):
            print('For inclusion in the Mycroft Marketplace a README.md file '
                  'is required. please add the file and retry.')
            results.append(False)
        else:
            results.append(True)

        with open(join(self.skill_dir, 'README.md')) as f:
            readme = f.read()
        if '# About' not in readme and '# Description' not in readme:
            print('README is missing About Section needed by the Marketplace')
            results.append(False)
        else:
            results.append(True)

        if '# Category' not in readme:
            print('README is missing Category section needed by the '
                  'Marketplace')
            results.append(False)
        else:
            results.append(True)
        return all(results)

    def perform(self):
        print('Uploading a new skill to the skill repo...')

        for i in listdir(self.entry.path):
            if i.lower() == 'readme.md' and i != 'README.md':
                shutil.move(join(self.entry.path, i), join(self.entry.path, 'README.md'))

        creator = CreateAction(None, self.entry.name.replace('-skill', ''))
        creator.path = self.entry.path
        creator.initialize_template({'.git', '.gitignore', 'README.md'})
        self.git.add('README.md')
        creator.commit_changes()

        try:
            skill_repo = creator.create_github_repo(
                lambda: input('Repo name:'))
        except GithubRepoExists:
            try:
                print("A repository with that name already exists")
                skill_repo = creator.link_github_repo(
                    lambda: input('Remote repo name:'))
            except UnrelatedGithubHistory:
                print("Repository history does not seem to be related")
                skill_repo = creator.force_push(
                    lambda: input('Confirm repo name:'))
        if skill_repo:
            self.entry.url = skill_repo.html_url
            self.entry.author = self.user.login
        else:
            if not self.entry.url:
                raise NoGitRepository
            skill_repo = self.github.get_repo(skill_repo_name(self.entry.url))

        if not skill_repo.permissions.push:
            print('Warning: You do not have write permissions to the provided skill repo.')
            if ask_yes_no('Create a fork and use that instead? (Y/n)', True):
                skill_repo = self.user.create_fork(skill_repo)
                print('Created fork:', skill_repo.html_url)
                self.git.remote('rename', 'origin', 'upstream')
                self.git.remote('add', 'origin', skill_repo.html_url)

        # verify that the required files exists in origin and contain the
        # required content.
        if not self.check_valid():
            print("Please add the missing information and rerun the command.")
            return

        self.entry.name = input('Enter a unique skill name (ie. npr-news or grocery-list): ')

        readme_file = {i.lower(): i for i in os.listdir(self.entry.path)}['readme.md']
        readme = read_file(self.entry.path, readme_file)

        last_section = None
        sections = {last_section: ''}
        for line in readme.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                last_section = line.strip('# ').lower()
                sections[last_section] = ''
            else:
                sections[last_section] += '\n' + line
        del sections[None]

        if 'about' in sections:
            description = sections['about']
        elif 'description' in sections:
            description = sections['description']

        branch = SkillData(self.entry).add_to_repo()
        self.repo.push_to_fork(branch)

        pull = create_or_edit_pr(
            title='Add {}'.format(self.entry.name), body=body_template.format(
                description=description, skill_name=self.entry.name, skill_url=skill_repo.html_url
            ), user=self.user, branch=branch, skills_repo=self.repo.hub,
            repo_branch=self.branch
        )

        print('Created pull request: ', pull.html_url)
