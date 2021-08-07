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
from contextlib import suppress
from git import Git, GitCommandError
from github.Repository import Repository
from msm import SkillRepo, SkillEntry
from os.path import join
from subprocess import call

from msk.exceptions import AlreadyUpdated, NotUploaded
from msk.global_context import GlobalContext
from msk.lazy import Lazy
from msk.util import skill_repo_name


class RepoData(GlobalContext):
    msminfo = Lazy(lambda s: s.msm.repo)  # type: SkillRepo
    git = Lazy(lambda s: Git(s.msminfo.path))  # type: Git
    hub = Lazy(lambda s: s.github.get_repo(skill_repo_name(s.msminfo.url)))  # type: Repository
    fork = Lazy(lambda s: s.github.get_user().create_fork(s.hub))  # type: Repository

    def push_to_fork(self, branch: str):
        remotes = self.git.remote().split('\n')
        command = 'set-url' if 'fork' in remotes else 'add'
        self.git.remote(command, 'fork', self.fork.html_url)

        # Use call to ensure the environment variable GIT_ASKPASS is used
        call(['git', 'push', '-u', 'fork', branch, '--force'], cwd=self.msminfo.path)

    def checkout_branch(self, branch):
        with suppress(GitCommandError):
            self.git.branch('-D', branch)
        try:
            self.git.checkout(b=branch)
        except GitCommandError:
            self.git.checkout(branch)


class SkillData(GlobalContext):
    def __init__(self, skill: SkillEntry):
        self.entry = skill

    name = property(lambda self: self.entry.name)
    repo = Lazy(lambda s: RepoData())  # type: RepoData
    repo_git = Lazy(lambda s: Git(join(s.repo.msminfo.path, s.submodule_name)))  # type: Git
    repo_branch = Lazy(lambda s: s.repo_git.symbolic_ref('refs/remotes/origin/HEAD'))
    git = Lazy(lambda s: Git(s.entry.path))  # type: Git
    hub = Lazy(lambda s: s.github.get_repo(skill_repo_name(s.entry.url)))  # type: Repository

    @Lazy
    def submodule_name(self):
        name_to_path = {name: path for name, path, url, sha in self.repo.msminfo.get_skill_data()}
        if self.name not in name_to_path:
            raise NotUploaded('The skill {} has not yet been uploaded to the skill store'.format(
                self.name
            ))
        return name_to_path[self.name]

    def upgrade(self) -> str:
        skill_module = self.submodule_name
        submod = Git(join(self.repo.msminfo.path, skill_module))
        submod.remote('set-head', 'origin', '-a')
        self.repo.msminfo.update()
        self.repo_git.fetch()
        self.repo_git.reset(self.repo_branch, hard=True)

        upgrade_branch = 'upgrade-' + self.name
        self.repo.checkout_branch(upgrade_branch)

        if not self.repo.git.diff(skill_module) and self.repo.git.ls_files(skill_module):
            raise AlreadyUpdated(
                'The latest version of {} is already uploaded to the skill repo'.format(
                    self.name
                )
            )
        self.repo.git.add(skill_module)
        self.repo.git.commit(message='Upgrade ' + self.name)
        return upgrade_branch

    def add_to_repo(self) -> str:
        self.repo.msminfo.update()
        existing_mods = [i.split('\t')[1]
                         for i in self.git.ls_tree('HEAD').split('\n')]
        if self.name not in existing_mods:
            self.repo.git.submodule('add', self.entry.url, self.name)

        # Upgrade skill in case it is outdated
        self.repo_git.fetch()
        self.repo_git.reset(self.repo_branch, hard=True)

        branch_name = 'add-' + self.name
        self.repo.checkout_branch(branch_name)
        self.repo.git.add(self.name)
        self.repo.git.commit(message='Add ' + self.name)
        return branch_name

    def init_existing(self):
        self.repo.git.submodule('update', '--init', self.submodule_name)
