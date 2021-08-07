# Copyright (c) 2018 Mycroft AI, Inc.
#
# This file is part of Mycroft Skills Manager
# (see https://github.com/MatthewScholefield/mycroft-light).
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
from glob import glob
from os import makedirs
from os.path import exists, join, isdir, dirname, basename, normpath
import json

from git import Repo
from git.exc import GitCommandError, GitError

from msm import git_to_msm_exceptions
from msm.exceptions import MsmException
from msm.util import cached_property, Git
import logging
import requests

LOG = logging.getLogger(__name__)

MYCROFT_SKILLS_DATA = "https://raw.githubusercontent.com/MycroftAI/mycroft-skills-data"
FIVE_MINUTES = 300

def load_skills_data(branch, path):
    try:
        market_info_url = (MYCROFT_SKILLS_DATA + "/" + branch +
                           "/skill-metadata.json")
        info = requests.get(market_info_url).json()
        # Cache the received data
        with open(path, 'w') as f:
            try:
                json.dump(info, f)
            except Exception as e:
                LOG.warning('Couldn\'t save cached version of '
                            'skills-metadata.json')
        return {info[k]['repo'].lower(): info[k] for k in info}
    except (requests.HTTPError, requests.exceptions.ConnectionError):
        pass
    except Exception as e:
        LOG.warning("Skill metadata couldn't be fetched ({})".format(repr(e)))

    # Try to load cache if fetching failed
    if exists(path):
        with open(path) as f:
            try:
                info = json.load(f)
            except Exception:
                LOG.warning('skills-metadata cache exists but can\'t '
                            'be parsed')
                return {}
        return {info[k]['repo'].lower(): info[k] for k in info}
    else:
        return {}


class SkillRepo(object):
    def __init__(self, path=None, url=None, branch=None):
        self.path = path or "/opt/mycroft/.skills-repo"
        self.url = url or "https://github.com/MycroftAI/mycroft-skills"
        self.branch = branch or "21.02"
        self.repo_info = {}

    @cached_property(ttl=FIVE_MINUTES)
    def skills_meta_info(self):
        try:
            skills_meta_cache = normpath(join(self.path,
                                              '..', '.skills-meta.json'))
            skills_meta_info = load_skills_data(self.branch,
                                                skills_meta_cache)
        except Exception as e:
            LOG.exception(repr(e))
            skills_meta_info = {}

        return skills_meta_info

    def read_file(self, filename):
        with open(join(self.path, filename)) as f:
            return f.read()

    def __prepare_repo(self):
        LOG.info('[Flow Learning] .venv.lib.python3.8/site-packages/msm/skill_repo.py/SkillRepo.__prepare_repo, fetch from git self.url=' + self.url + ' path=' + self.path )
        if not exists(dirname(self.path)):
            makedirs(dirname(self.path))

        if not isdir(self.path):
            Repo.clone_from(self.url, self.path)

        git = Git(self.path)
        git.config('remote.origin.url', self.url)
        git.fetch()

        try:
            git.checkout(self.branch)
            git.reset('origin/' + self.branch, hard=True)
        except GitCommandError:
            raise MsmException('Invalid branch: ' + self.branch)

    def update(self):
        try:
            self.__prepare_repo()
        except (GitError, PermissionError) as e:
            LOG.warning('Could not prepare repo ({}), '
                        ' Creating temporary repo'.format(repr(e)))
            original_path = self.path
            self.path = '/tmp/.skills-repo'
            try:
                with git_to_msm_exceptions():
                    self.__prepare_repo()
            except Exception:
                LOG.warning('Could not use temporary repo either ({}), '
                            ' trying to use existing one without '
                            'update'.format(repr(e)))
                self.path = original_path  # Restore path to previous value
                raise

    def get_skill_data(self):
        """ generates tuples of name, path, url, sha """
        path_to_sha = {
            folder: sha for folder, sha in self.get_shas()
        }
        modules = self.read_file('.gitmodules').split('[submodule "')
        for i, module in enumerate(modules):
            if not module:
                continue
            try:
                name = module.split('"]')[0].strip()
                path = module.split('path = ')[1].split('\n')[0].strip()
                url = module.split('url = ')[1].strip()
                sha = path_to_sha.get(path, '')
                yield name, path, url, sha
            except (ValueError, IndexError) as e:
                LOG.warning('Failed to parse submodule "{}" #{}:{}'.format(
                    locals().get('name', ''), i, e
                ))

    def get_shas(self):
        git = Git(self.path)
        with git_to_msm_exceptions():
            shas = git.ls_tree('origin/' + self.branch)
        for line in shas.split('\n'):
            size, typ, sha, folder = line.split()
            if typ != 'commit':
                continue
            yield folder, sha

    def get_default_skill_names(self):
        for defaults_file in glob(join(self.path, 'DEFAULT-SKILLS*')):
            with open(defaults_file) as f:
                skills = list(filter(
                    lambda x: x and not x.startswith('#'),
                    map(str.strip, f.read().split('\n'))
                ))
            platform = basename(defaults_file).replace('DEFAULT-SKILLS', '')
            platform = platform.replace('.', '') or 'default'
            yield platform, skills
