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
from argparse import ArgumentParser
from genericpath import samefile
from git import Git
from github.Repository import Repository
from msm import MycroftSkillsManager

from msk.console_action import ConsoleAction
from msk.exceptions import NotUploaded
from msk.repo_action import SkillData
from msk.util import skills_kit_footer, create_or_edit_pr

body_template = '''
This upgrades {skill_name} to include the following new commits:

{commits}

''' + skills_kit_footer


class UpgradeAction(ConsoleAction):
    def __init__(self, args):
        msm = MycroftSkillsManager()
        skill_matches = [
            skill
            for skill in msm.list()
            if skill.is_local and samefile(skill.path, args.skill_folder)
        ]
        if not skill_matches:
            raise NotUploaded('Skill at folder not uploaded to store: {}'.format(args.skill_folder))

        self.skill = SkillData(skill_matches[0])
        self.skill.init_existing()  # Verifies the skill exists

    @staticmethod
    def register(parser: ArgumentParser):
        pass  # Implemented in SubmitAction

    def create_pr_message(self, skill_git: Git, skill_repo: Repository) -> tuple:
        """Reads git commits from skill repo to create a list of changes as the PR content"""
        title = 'Upgrade ' + self.skill.name
        body = body_template.format(
            skill_name=self.skill.name,
            commits='\n'.join(
                ' - [{}]({})'.format(
                    skill_git.show('-s', sha, format='%s'),
                    skill_repo.get_commit(sha).html_url
                )
                for sha in skill_git.rev_list(
                    '--ancestry-path', '{}..{}'.format(self.skill.entry.sha, 'HEAD')
                ).split('\n')
            )
        )
        return title, body

    def perform(self):
        print('Upgrading an existing skill in the skill repo...')
        upgrade_branch = self.skill.upgrade()
        self.repo.push_to_fork(upgrade_branch)
        title, body = self.create_pr_message(self.skill.git, self.skill.hub)
        print()
        print('===', title, '===')
        print(body)
        print()
        pull = create_or_edit_pr(title, body, self.repo.hub, self.user, upgrade_branch, self.branch)
        print('Created PR at:', pull.html_url)
