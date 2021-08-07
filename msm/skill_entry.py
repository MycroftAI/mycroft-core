# Copyright (c) 2018 Mycroft AI, Inc.
#
# This file is part of Mycroft Skills Manager
# (see https://github.com/MycroftAI/mycroft-skills-manager).
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import sys

import logging
import os
import shutil
import subprocess
import yaml
from contextlib import contextmanager
from difflib import SequenceMatcher
from functools import wraps
from git import Repo, GitError
from git.exc import GitCommandError
from lazy import lazy
from os.path import exists, join, basename, dirname, isfile
from shutil import rmtree, move
from subprocess import PIPE, Popen
from tempfile import mktemp, gettempdir
from threading import Lock
from typing import Callable
from pako import PakoManager

from msm import SkillRequirementsException, git_to_msm_exceptions
from msm.exceptions import PipRequirementsException, \
    SystemRequirementsException, AlreadyInstalled, SkillModified, \
    AlreadyRemoved, RemoveException, CloneException, NotInstalled, GitException
from msm.util import cached_property, Git

LOG = logging.getLogger(__name__)

# Branches which can be switched from when updating
# TODO Make this configurable
SWITCHABLE_BRANCHES = ['master']

# default constraints to use if no are given
DEFAULT_CONSTRAINTS = '/etc/mycroft/constraints.txt'
FIVE_MINUTES = 300


@contextmanager
def work_dir(directory):
    old_dir = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(old_dir)


def _backup_previous_version(func: Callable = None):
    """Private decorator to back up previous skill folder"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.old_path = None
        if self.is_local:
            self.old_path = join(gettempdir(), self.name)
            if exists(self.old_path):
                rmtree(self.old_path)
            shutil.copytree(self.path, self.old_path)
        try:
            func(self, *args, **kwargs)

        # Modified skill or GitError should not restore working copy
        except (SkillModified, GitError, GitException):
            raise
        except Exception:
            LOG.info('Problem performing action. Restoring skill to '
                     'previous state...')
            if exists(self.path):
                rmtree(self.path)
            if self.old_path and exists(self.old_path):
                shutil.copytree(self.old_path, self.path)
            self.is_local = exists(self.path)
            raise
        finally:
            # Remove temporary path if needed
            if self.old_path and exists(self.old_path):
                rmtree(self.old_path)

    return wrapper


class SkillEntry(object):
    pip_lock = Lock()
    manifest_yml_format = {
        'dependencies': {
            'system': {},
            'exes': [],
            'skill': [],
            'python': []
        }
    }

    def __init__(self, name, path, url='', sha='', msm=None):
        url = url.rstrip('/')
        url = url[:-len('.git')] if url.endswith('.git') else url
        self.path = path
        self.url = url
        self.sha = sha
        self.msm = msm
        if msm:
            u = url.lower()
            self.meta_info = msm.repo.skills_meta_info.get(u, {})
        else:
            self.meta_info = {}
        if name is not None:
            self.name = name
        elif 'name' in self.meta_info:
            self.name = self.meta_info['name']
        else:
            self.name = basename(path)

        # TODO: Handle git:// urls as well
        from_github = False
        if url.startswith('https://'):
            url_tokens = url.rstrip("/").split("/")
            from_github = url_tokens[-3] == 'github.com' if url else False
        self.author = self.extract_author(url) if from_github else ''
        self.id = self.extract_repo_id(url) if from_github else self.name
        self.is_local = exists(path)
        self.old_path = None  # Path of previous version while upgrading

    @property
    def is_beta(self):
        return not self.sha or self.sha == 'HEAD'

    @property
    def is_dirty(self):
        """True if different from the version in the mycroft-skills repo.

        Considers a skill dirty if
        - the checkout sha doesn't match the mycroft-skills repo
        - the skill doesn't exist in the mycroft-skills repo
        - the skill is not a git repo
        - has local modifications
        """
        if not exists(self.path):
            return False
        try:
            checkout = Git(self.path)
            mod = checkout.status(porcelain=True, untracked_files='no') != ''
            current_sha = checkout.rev_parse('HEAD')
        except GitCommandError:  # Not a git checkout
            return True

        skill_shas = {d[0]: d[3] for d in self.msm.repo.get_skill_data()}
        return (self.name not in skill_shas or
                current_sha != skill_shas[self.name] or
                mod)

    @cached_property(ttl=FIVE_MINUTES)
    def skill_gid(self):
        """Format skill gid for the skill.

        This property does some Git gymnastics to determine its return value.
        When a device boots, each skill accesses this property several times.
        To reduce the amount of boot time, cache the value returned by this
        property.  Cache expires five minutes after it is generated.
        """
        LOG.debug('Generating skill_gid for ' + self.name)
        gid = ''
        if self.is_dirty:
            gid += '@|'
        if self.meta_info != {}:
            gid += self.meta_info['skill_gid']
        else:
            name = self.name.split('.')[0]
            gid += name
        return gid

    def __str__(self):
        return self.name

    def attach(self, remote_entry):
        """Attach a remote entry to a local entry"""
        self.name = remote_entry.name
        self.sha = remote_entry.sha
        self.url = remote_entry.url
        self.author = remote_entry.author
        return self

    @classmethod
    def from_folder(cls, path, msm=None, use_cache=True):
        """Find or create skill entry from folder path.

        Arguments:
            path:       path of skill folder
            msm:        msm instance to use for caching and extended information
                        retrieval.
            use_cache:  Enable/Disable cache usage. defaults to True
        """
        LOG.info('[Flow Learning] in msm.skill_entry.py SKillEntry.from_folder.')
        if msm and use_cache:
            skills = {skill.path: skill for skill in msm.local_skills.values()}
            if path in skills:
                return skills[path]
        # Shore: todo zh disable git
        url = ''
        if False:
            url = cls.find_git_url(path)
        return cls(None, path, url, msm=msm)

    @classmethod
    def create_path(cls, folder, url, name=''):
        return join(folder, '{}.{}'.format(
            name or cls.extract_repo_name(url), cls.extract_author(url)
        ).lower())

    @staticmethod
    def extract_repo_name(url):
        s = url.rstrip('/').split("/")[-1]
        a, b, c = s.rpartition('.git')
        if not c:
            return a
        return s

    @staticmethod
    def extract_author(url):
        return url.rstrip('/').split("/")[-2].split(':')[-1]

    @classmethod
    def extract_repo_id(cls, url):
        return '{}:{}'.format(cls.extract_author(url).lower(),
                              cls.extract_repo_name(url)).lower()

    @staticmethod
    def _tokenize(x):
        return x.replace('-', ' ').split()

    @staticmethod
    def _extract_tokens(s, tokens):
        s = s.lower().replace('-', ' ')
        extracted = []
        for token in tokens:
            extracted += [token] * s.count(token)
            s = s.replace(token, '')
        s = ' '.join(i for i in s.split(' ') if i)
        tokens = [i for i in s.split(' ') if i]
        return s, tokens, extracted

    @classmethod
    def _compare(cls, a, b):
        return SequenceMatcher(a=a, b=b).ratio()

    def match(self, query, author=None):
        search, search_tokens, search_common = self._extract_tokens(
            query, ['skill', 'fallback', 'mycroft']
        )

        name, name_tokens, name_common = self._extract_tokens(
            self.name, ['skill', 'fallback', 'mycroft']
        )

        weights = [
            (9, self._compare(name, search)),
            (9, self._compare(name.split(' '), search_tokens)),
            (2, self._compare(name_common, search_common)),
        ]
        if author:
            author_weight = self._compare(self.author, author)
            weights.append((5, author_weight))
            author_weight = author_weight
        else:
            author_weight = 1.0
        return author_weight * (
                sum(weight * val for weight, val in weights) /
                sum(weight for weight, val in weights)
        )

    def run_pip(self, constraints=None):
        if not self.dependent_python_packages:
            return False

        # Use constraints to limit the installed versions
        if constraints and not exists(constraints):
            LOG.error('Couldn\'t find the constraints file')
            return False
        elif exists(DEFAULT_CONSTRAINTS):
            constraints = DEFAULT_CONSTRAINTS

        LOG.info('Installing requirements.txt for ' + self.name)
        can_pip = os.access(dirname(sys.executable), os.W_OK | os.X_OK)
        pip_args = [sys.executable, '-m', 'pip', 'install']
        if constraints:
            pip_args += ['-c', constraints]

        if not can_pip:
            pip_args = ['sudo', '-n'] + pip_args

        with self.pip_lock:
            """
            Iterate over the individual Python packages and
            install them one by one to enforce the order specified
            in the manifest.
            """
            for dependent_python_package in self.dependent_python_packages:
                pip_command = pip_args + [dependent_python_package]
                proc = Popen(pip_command, stdout=PIPE, stderr=PIPE)
                pip_code = proc.wait()
                if pip_code != 0:
                    stderr = proc.stderr.read().decode()
                    if pip_code == 1 and 'sudo:' in stderr and pip_args[0] == 'sudo':
                        raise PipRequirementsException(
                            2, '', 'Permission denied while installing pip '
                                   'dependencies. Please run in virtualenv or use sudo'
                        )
                    raise PipRequirementsException(
                        pip_code, proc.stdout.read().decode(), stderr
                    )

        return True

    def install_system_deps(self):
        self.run_requirements_sh()
        system_packages = {
            exe: (packages or '').split()
            for exe, packages in self.dependent_system_packages.items()
        }
        LOG.info('Installing system requirements...')
        all_deps = system_packages.pop('all', [])
        try:
            manager = PakoManager()
            success = manager.install(all_deps, overrides=system_packages)
        except RuntimeError as e:
            LOG.warning('Failed to launch package manager: {}'.format(e))
            success = False
        missing_exes = [
            exe for exe in self.dependencies.get('exes') or []
            if not shutil.which(exe)
        ]
        if missing_exes:
            if not success:
                LOG.warning('Failed to install dependencies.')
                if all_deps:
                    LOG.warning('Please install manually: {}'.format(
                        ' '.join(all_deps)
                    ))
            raise SkillRequirementsException('Could not find exes: {}'.format(
                ', '.join(missing_exes)
            ))
        return success

    def run_requirements_sh(self):
        setup_script = join(self.path, "requirements.sh")
        if not exists(setup_script):
            return False

        with work_dir(self.path):
            rc = subprocess.call(["bash", setup_script])

        if rc != 0:
            LOG.error("Requirements.sh failed with error code: " + str(rc))
            raise SystemRequirementsException(rc)
        LOG.info("Successfully ran requirements.sh for " + self.name)
        return True

    def run_skill_requirements(self):
        if not self.msm:
            raise ValueError('Pass msm to SkillEntry to install skill deps')
        try:
            for skill_dep in self.dependent_skills:
                LOG.info("Installing skill dependency: {}".format(skill_dep))
                try:
                    self.msm.install(skill_dep)
                except AlreadyInstalled:
                    pass
        except Exception as e:
            raise SkillRequirementsException(e)

    def verify_info(self, info, fmt):
        if not info:
            return
        if not isinstance(info, type(fmt)):
            LOG.warning('Invalid value type manifest.yml for {}: {}'.format(
                self.name, type(info)
            ))
            return
        if not isinstance(info, dict) or not fmt:
            return
        for key in info:
            if key not in fmt:
                LOG.warning('Unknown key in manifest.yml for {}: {}'.format(
                    self.name, key
                ))
                continue
            self.verify_info(info[key], fmt[key])

    @lazy
    def skill_info(self):
        yml_path = join(self.path, 'manifest.yml')
        if exists(yml_path):
            LOG.info('Reading from manifest.yml')
            with open(yml_path) as f:
                info = yaml.safe_load(f)
                self.verify_info(info, self.manifest_yml_format)
                return info or {}
        return {}

    @lazy
    def dependencies(self):
        return self.skill_info.get('dependencies') or {}

    @lazy
    def dependent_skills(self):
        skills = set()
        reqs = join(self.path, "skill_requirements.txt")
        if exists(reqs):
            with open(reqs, "r") as f:
                for i in f.readlines():
                    skill = i.strip()
                    if skill:
                        skills.add(skill)
        for i in self.dependencies.get('skill') or []:
            skills.add(i)
        return list(skills)

    @lazy
    def dependent_python_packages(self):
        reqs = join(self.path, "requirements.txt")
        req_lines = []
        if exists(reqs):
            with open(reqs, "r") as f:
                req_lines += f.readlines()
        req_lines += self.dependencies.get('python') or []
        # Strip comments
        req_lines = [l.split('#')[0].strip() for l in req_lines]
        return [i for i in req_lines if i]  # Strip empty lines

    @lazy
    def dependent_system_packages(self):
        return self.dependencies.get('system') or {}

    def remove(self):
        if not self.is_local:
            raise AlreadyRemoved(self.name)
        try:
            rmtree(self.path)
            self.is_local = False
        except OSError as e:
            raise RemoveException(str(e))

        LOG.info('Successfully removed ' + self.name)

    @_backup_previous_version
    def install(self, constraints=None):
        if self.is_local:
            raise AlreadyInstalled(self.name)

        LOG.info("Downloading skill: " + self.url)
        try:
            tmp_location = mktemp()
            Repo.clone_from(self.url, tmp_location)
            self.is_local = True
            Git(tmp_location).reset(self.sha or 'HEAD', hard=True)
        except GitCommandError as e:
            raise CloneException(e.stderr)

        if isfile(join(tmp_location, '__init__.py')):
            move(join(tmp_location, '__init__.py'),
                 join(tmp_location, '__init__'))

        try:
            move(tmp_location, self.path)

            if self.msm:
                self.run_skill_requirements()
            self.install_system_deps()
            self.run_pip(constraints)
        finally:
            if isfile(join(self.path, '__init__')):
                move(join(self.path, '__init__'),
                     join(self.path, '__init__.py'))

        LOG.info('Successfully installed ' + self.name)

    def update_deps(self, constraints=None):
        if self.msm:
            self.run_skill_requirements()
        self.install_system_deps()
        self.run_pip(constraints)

    def _find_sha_branch(self):
        git = Git(self.path)
        sha_branches = git.branch(
            contains=self.sha, all=True
        ).split('\n')
        sha_branch = [b for b in sha_branches if ' -> ' not in b][0]
        sha_branch = sha_branch.strip('* \n').replace('remotes/', '')
        for remote in git.remote().split('\n'):
            sha_branch = sha_branch.replace(remote + '/', '')
        return sha_branch

    @_backup_previous_version
    def update(self):
        if not self.is_local:
            raise NotInstalled('{} is not installed'.format(self.name))
        git = Git(self.path)

        with git_to_msm_exceptions():
            sha_before = git.rev_parse('HEAD')

            modified_files = git.status(porcelain=True, untracked='no')
            if modified_files != '':
                raise SkillModified('Uncommitted changes:\n' + modified_files)

            git.fetch()
            current_branch = git.rev_parse('--abbrev-ref', 'HEAD').strip()
            if self.sha and current_branch in SWITCHABLE_BRANCHES:
                # Check out correct branch
                git.checkout(self._find_sha_branch())

            git.merge(self.sha or 'origin/HEAD', ff_only=True)

        sha_after = git.rev_parse('HEAD')

        if sha_before != sha_after:
            self.update_deps()
            LOG.info('Updated ' + self.name)
            # Trigger reload by modifying the timestamp
            os.utime(join(self.path, '__init__.py'))
            return True
        else:
            LOG.info('Nothing new for ' + self.name)
            return False

    @staticmethod
    def find_git_url(path):
        """Get the git url from a folder"""
        LOG.info(
                '[Flow Learning] Attempting to retrieve the remote origin URL config for '
                'skill in path ' + path
            )
        try:
            LOG.debug(
                'Attempting to retrieve the remote origin URL config for '
                'skill in path ' + path
            )
            return Git(path).config('remote.origin.url')
        except GitError:
            return ''

    def __repr__(self):
        return '<SkillEntry {}>'.format(' '.join(
            '{}={}'.format(attr, self.__dict__[attr])
            for attr in ['name', 'author', 'is_local']
        ))
