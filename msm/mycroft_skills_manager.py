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
"""Install, remove, update and track the skills on a device

MSM can be used on the command line but is also used by Mycroft core daemons.
"""
import time
import logging
from functools import wraps
from glob import glob
from multiprocessing.pool import ThreadPool
from os import path
from typing import Dict, List

from msm import GitException
from msm.exceptions import (
    AlreadyInstalled,
    AlreadyRemoved,
    MsmException,
    MultipleSkillMatches,
    RemoveException,
    SkillNotFound
)
from msm.skill_entry import SkillEntry
from msm.skill_repo import SkillRepo
from msm.skill_state import (
    initialize_skill_state,
    get_skill_state,
    write_device_skill_state,
    load_device_skill_state,
    device_skill_state_hash
)
from msm.util import cached_property, MsmProcessLock

LOG = logging.getLogger(__name__)

CURRENT_SKILLS_DATA_VERSION = 2
ONE_DAY = 86400


def save_device_skill_state(func):
    """Decorator to overwrite the skills.json file when skill state changes.

    The methods decorated with this function are executed in threads.  So,
    this contains some funky logic to keep the threads from stepping on one
    another.
    """
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        will_save = False
        if not self.saving_handled:
            will_save = self.saving_handled = True
        try:
            ret = func(self, *args, **kwargs)
        finally:
            if will_save:
                self.write_device_skill_state()
            # Always restore saving_handled flag
            if will_save:
                self.saving_handled = False

        return ret

    return func_wrapper


class MycroftSkillsManager(object):
    SKILL_GROUPS = {'default', 'mycroft_mark_1', 'picroft', 'kde',
                    'respeaker', 'mycroft_mark_2', 'mycroft_mark_2pi'}
    DEFAULT_SKILLS_DIR = "/opt/mycroft/skills"

    def __init__(self, platform='default', skills_dir=None, repo=None,
                 versioned=True):
        self.platform = platform
        self.skills_dir = (
                path.expanduser(skills_dir or '') or self.DEFAULT_SKILLS_DIR
        )
        self.repo = repo or SkillRepo()
        self.versioned = versioned
        self.lock = MsmProcessLock()

        # Property placeholders
        self._all_skills = None
        self._default_skills = None
        self._local_skills = None
        self._device_skill_state = None

        self.saving_handled = False
        self.device_skill_state_hash = ''
        with self.lock:
            self._init_skills_data()

    def clear_cache(self):
        """Completely clear the skills cache."""
        self._device_skill_state = None
        self._invalidate_skills_cache()

    @cached_property(ttl=ONE_DAY)
    def all_skills(self):
        """Getting a list of skills can take a while so cache it.

        The list method is called several times in this class and in core.
        Skill data on a device just doesn't change that frequently so
        getting a fresh list that many times does not make a lot of sense.
        The cache will expire every hour to pick up any changes in the
        mycroft-skills repo.

        Skill installs and updates will invalidate the cache, which will
        cause this property to refresh next time is is referenced.

        The list method can be called directly if a fresh skill list is needed.
        """
        LOG.info('[Flow Learning] .venv/lib/python3.8/site-packages/msm/mycroft_skills_manager.py.MycroftSkillsManager.all_skills()')
        if self._all_skills is None:
            self._all_skills = self._get_all_skills()

        return self._all_skills

    def _get_all_skills(self):
        LOG.info('[Flow Learning] .venv/lib/python3.8/site-packages/msm/mycroft_skills_manager.py.MycroftSkillsManager._get_all_skills')
        LOG.info('building SkillEntry objects for all skills')
        
        # Shore: disable get remote skills
        remote_skills = []
        if False:
            self._refresh_skill_repo()
            remote_skills = self._get_remote_skills()
        else:
            LOG.info('[Flow Learning] in msm.mycroft_skills_manager.py.MycroftSkillsManager._get_all_skills, do not get remote skills.')
        all_skills = self._merge_remote_with_local(remote_skills)

        return all_skills

    def list(self):
        """Load a list of SkillEntry objects from both local and remote skills

        It is necessary to load both local and remote skills at
        the same time to correctly associate local skills with the name
        in the repo and remote skills with any custom path that they
        have been downloaded to.

        The return value of this function is cached in the all_skills property.
        Only call this method if you need a fresh version of the SkillEntry
        objects.
        """
        LOG.info('[Flow Learning] .venv/lib/python3.8/site-packages/msm/mycroft_skills_manager.py.MycroftSkillsManager.list()')
        all_skills = self._get_all_skills()
        self._invalidate_skills_cache(new_value=all_skills)

        return all_skills

    def _refresh_skill_repo(self):
        """Get the latest mycroft-skills repo code."""
        try:
            self.repo.update()
        except GitException as e:
            if not path.isdir(self.repo.path):
                raise
            LOG.warning('Failed to update repo: {}'.format(repr(e)))

    def _get_remote_skills(self):
        """Build a dictionary of skills in mycroft-skills repo keyed by id"""
        LOG.info('[Flow Learning] in .venv ... msm.mycroft_skills_mamager.py. MycroftSkillsManager._get_remote_skills')
        remote_skills = []
        for name, _, url, sha in self.repo.get_skill_data():
            skill_dir = SkillEntry.create_path(self.skills_dir, url, name)
            LOG.info('[Flow Learning] in .venv ... msm.mycroft_skills_mamager.py. MycroftSkillsManager._get_remote_skills ' + name + ' skill_dir='+ skill_dir + ' url=' + url)
            sha = sha if self.versioned else ''
            remote_skills.append(
                SkillEntry(name, skill_dir, url, sha, msm=self)
            )

        return {skill.id: skill for skill in remote_skills}

    def _merge_remote_with_local(self, remote_skills):
        """Merge the skills found in the repo with those installed locally."""
        LOG.info('[Flow Learning] in .venv ... msm.mycroft_skills_mamager.py. MycroftSkillsManager._merge_remote_with_local')
        all_skills = []
        LOG.info('[Flow Learning] in .venv ... msm.mycroft_skills_mamager.py. MycroftSkillsManager._merge_remote_with_local  skills_dir =' + self.skills_dir)   
        for skill_file in glob(path.join(self.skills_dir, '*', '__init__.py')):
            LOG.info('[Flow Learning] in .venv ... msm.mycroft_skills_mamager.py. MycroftSkillsManager._merge_remote_with_local  in for loop. skill_flie ' + skill_file)   
            skill = SkillEntry.from_folder(path.dirname(skill_file), msm=self,
                                        use_cache=False)

            LOG.info('[Flow Learning] in .venv ... msm.mycroft_skills_mamager.py. MycroftSkillsManager._merge_remote_with_local  in for loop2.')   
            if skill.id in remote_skills:
                LOG.info('[Flow Learning] in .venv ... msm.mycroft_skills_mamager.py. MycroftSkillsManager._merge_remote_with_local  in for loop3.')   
                skill.attach(remote_skills.pop(skill.id))
            LOG.info('[Flow Learning] in .venv ... msm.mycroft_skills_mamager.py. MycroftSkillsManager._merge_remote_with_local  in for loop4.')   
            all_skills.append(skill)
        LOG.info('[Flow Learning] in .venv ... msm.mycroft_skills_mamager.py. MycroftSkillsManager._merge_remote_with_local remote_skills = ' + str(remote_skills))
        if len(remote_skills) > 0:
            all_skills.extend(remote_skills.values())

        return all_skills

    @property
    def local_skills(self):
        """Property containing a dictionary of local skills keyed by name."""
        if self._local_skills is None:
            self._local_skills = {
                s.name: s for s in self.all_skills if s.is_local
            }

        return self._local_skills

    @property
    def default_skills(self):
        if self._default_skills is None:
            default_skill_groups = self.list_all_defaults()
            try:
                default_skill_group = default_skill_groups[self.platform]
            except KeyError:
                LOG.error(
                    'No default skill list found for platform "{}".  '
                    'Using base list.'.format(self.platform)
                )
                default_skill_group = default_skill_groups.get('default', [])
            self._default_skills = {s.name: s for s in default_skill_group}

        return self._default_skills

    def list_all_defaults(self):  # type: () -> Dict[str, List[SkillEntry]]
        """Generate dictionary of default skills in all default skill groups"""
        all_skills = {skill.name: skill for skill in self.all_skills}
        default_skills = {group: [] for group in self.SKILL_GROUPS}

        for group_name, skill_names in self.repo.get_default_skill_names():
            group_skills = []
            for skill_name in skill_names:
                try:
                    group_skills.append(all_skills[skill_name])
                except KeyError:
                    LOG.warning('No such default skill: ' + skill_name)
            default_skills[group_name] = group_skills

        return default_skills

    def _init_skills_data(self):
        """Initial load of the skill state that occurs upon instantiation.

        If the skills state was upgraded after it was loaded, write the
        updated skills state to disk.
        """
        try:
            del(self.device_skill_state['upgraded'])
        except KeyError:
            self.device_skill_state_hash = device_skill_state_hash(
                self.device_skill_state
            )
        else:
            self.write_device_skill_state()

    @property
    def device_skill_state(self):
        """Dictionary representing the state of skills on a device."""
        if self._device_skill_state is None:
            self._device_skill_state = load_device_skill_state()
            skills_data_version = self._device_skill_state.get('version', 0)
            if skills_data_version < CURRENT_SKILLS_DATA_VERSION:
                self._upgrade_skills_data()
            else:
                self._sync_device_skill_state()

        return self._device_skill_state

    def _upgrade_skills_data(self):
        """Upgrade the contents of the device skills state if needed."""
        if self._device_skill_state.get('version', 0) == 0:
            self._upgrade_to_v1()
        if self._device_skill_state['version'] == 1:
            self._upgrade_to_v2()

    def _upgrade_to_v1(self):
        """Upgrade the device skills state to version one."""
        self._device_skill_state.update(blacklist=[], version=1, skills=[])
        for skill in self.local_skills.values():
            skill_data = self._device_skill_state.get(skill.name, {})
            try:
                origin = skill_data['origin']
            except KeyError:
                origin = self._determine_skill_origin(skill)
            beta = skill_data.get('beta', False)
            skill_state = initialize_skill_state(
                skill.name,
                origin,
                beta,
                skill.skill_gid
            )
            skill_state['installed'] = skill_data.get('installed', 0)
            if isinstance(skill_state['installed'], bool):
                skill_state['installed'] = 0
            skill_state['updated'] = skill_data.get('updated', 0)
            self._device_skill_state['skills'].append(skill_state)
        self._device_skill_state.update(upgraded=True)

    def _upgrade_to_v2(self):
        """Upgrade the device skills state to version 2.

        This adds the skill_gid field to skill entries.
        """
        self._update_skill_gid()
        self._device_skill_state.update(version=2, upgraded=True)

    def _sync_device_skill_state(self):
        """Sync device's skill state with with actual skills on disk."""
        self._add_skills_to_state()
        self._remove_skills_from_state()
        self._update_skill_gid()

    def _add_skills_to_state(self):
        """Add local skill to state if it is not already there."""
        skill_names = [s['name'] for s in self._device_skill_state['skills']]
        for skill in self.local_skills.values():
            if skill.name not in skill_names:
                origin = self._determine_skill_origin(skill)
                skill_state = initialize_skill_state(
                    skill.name,
                    origin,
                    False,
                    skill.skill_gid
                )
                self._device_skill_state['skills'].append(skill_state)

    def _remove_skills_from_state(self):
        """Remove skills from state that no longer exist in the filesystem."""
        skills_to_remove = []
        for skill in self._device_skill_state['skills']:
            is_not_local = skill['name'] not in self.local_skills
            is_installed_state = skill['installation'] == 'installed'
            if is_not_local and is_installed_state:
                skills_to_remove.append(skill)

        for skill in skills_to_remove:
            self._device_skill_state['skills'].remove(skill)

    def _update_skill_gid(self):
        for skill in self._device_skill_state['skills']:
            try:
                local_skill = self.local_skills[skill['name']]
            except KeyError:
                skill['skill_gid'] = ''
            else:
                skill['skill_gid'] = local_skill.skill_gid

    def _determine_skill_origin(self, skill):
        if skill.name in self.default_skills:
            origin = 'default'
        elif skill.url:
            origin = 'cli'
        else:
            origin = 'non-msm'

        return origin

    def write_device_skill_state(self, data=None):
        """Write device's skill state to disk if it has been modified."""
        data = data or self.device_skill_state
        if device_skill_state_hash(data) != self.device_skill_state_hash:
            write_device_skill_state(data)
            self.device_skill_state_hash = device_skill_state_hash(data)

    @save_device_skill_state
    def install(self, param, author=None, constraints=None, origin=''):
        """Install by url or name"""
        if isinstance(param, SkillEntry):
            skill = param
        else:
            skill = self.find_skill(param, author)
        skill_state = initialize_skill_state(
            skill.name,
            origin,
            skill.is_beta,
            skill.skill_gid
        )
        try:
            skill.install(constraints)
        except AlreadyInstalled:
            log_msg = 'Skill {} already installed - ignoring install request'
            LOG.info(log_msg.format(skill.name))
            skill_state = None
            raise
        except MsmException as e:
            skill_state.update(
                installation='failed',
                status='error',
                failure_message=str(e)
            )
            raise
        else:
            skill_state.update(
                installed=time.time(),
                installation='installed',
                status='active',
                beta=skill.is_beta
            )
        finally:
            # Store the entry in the list
            if skill_state is not None:
                self.device_skill_state['skills'].append(skill_state)
                self._invalidate_skills_cache()

    @save_device_skill_state
    def remove(self, param, author=None):
        """Remove by url or name"""
        if isinstance(param, SkillEntry):
            skill = param
        else:
            skill = self.find_skill(param, author)
        try:
            skill.remove()
        except AlreadyRemoved:
            LOG.info('Skill {} has already been removed'.format(skill.name))
            raise
        except RemoveException:
            LOG.exception('Failed to remove skill ' + skill.name)
            raise
        else:
            remaining_skills = []
            for skill_state in self.device_skill_state['skills']:
                if skill_state['name'] != skill.name:
                    remaining_skills.append(skill_state)
            self.device_skill_state['skills'] = remaining_skills
            self._invalidate_skills_cache()

    def update_all(self):
        def update_skill(skill):
            entry = get_skill_state(skill.name, self.device_skill_state)
            if entry:
                entry['beta'] = skill.is_beta
            if skill.update():
                self._invalidate_skills_cache()
                self._device_skill_state = None
                if entry:
                    entry['updated'] = time.time()

        return self.apply(update_skill, self.local_skills.values())

    @save_device_skill_state
    def update(self, skill=None, author=None):
        """Update all downloaded skills or one specified skill."""
        if skill is None:
            return self.update_all()
        else:
            if isinstance(skill, str):
                skill = self.find_skill(skill, author)
            skill_state = get_skill_state(skill.name, self.device_skill_state)
            if skill_state:
                skill_state['beta'] = skill.is_beta
            if skill.update():
                # On successful update update the update value
                if skill_state:
                    skill_state['updated'] = time.time()
                    self._invalidate_skills_cache()

    @save_device_skill_state
    def apply(self, func, skills, max_threads=20):
        """Run a function on all skills in parallel"""

        def run_item(skill):
            try:
                func(skill)
                return True
            except MsmException as e:
                LOG.error('Error running {} on {}: {}'.format(
                    func.__name__, skill.name, repr(e)
                ))
                return False
            except:
                LOG.exception('Error running {} on {}:'.format(
                    func.__name__, skill.name
                ))

        with ThreadPool(max_threads) as tp:
            return tp.map(run_item, skills)

    @save_device_skill_state
    def install_defaults(self):
        """Installs the default skills, updates all others"""

        def install_or_update_skill(skill):
            if skill.is_local:
                self.update(skill)
            else:
                self.install(skill, origin='default')

        return self.apply(
            install_or_update_skill,
            self.default_skills.values()
        )

    def _invalidate_skills_cache(self, new_value=None):
        """Reset the cached skill lists in case something changed.

        The cached_property decorator builds a _cache instance attribute
        storing a dictionary of cached values.  Deleting from this attribute
        invalidates the cache.
        """
        LOG.info('invalidating skills cache')
        if hasattr(self, '_cache') and 'all_skills' in self._cache:
            del self._cache['all_skills']
        self._all_skills = None if new_value is None else new_value
        self._local_skills = None
        self._default_skills = None

    def find_skill(self, param, author=None, skills=None):
        # type: (str, str, List[SkillEntry]) -> SkillEntry
        """Find skill by name or url"""
        if param.startswith('https://') or param.startswith('http://'):
            repo_id = SkillEntry.extract_repo_id(param)
            for skill in self.all_skills:
                if skill.id == repo_id:
                    return skill
            name = SkillEntry.extract_repo_name(param)
            skill_directory = SkillEntry.create_path(self.skills_dir, param)
            return SkillEntry(name, skill_directory, param, msm=self)
        else:
            skill_confs = {
                skill: skill.match(param, author)
                for skill in skills or self.all_skills
            }
            best_skill, score = max(skill_confs.items(), key=lambda x: x[1])
            LOG.info('Best match ({}): {} by {}'.format(
                round(score, 2), best_skill.name, best_skill.author)
            )
            if score < 0.3:
                raise SkillNotFound(param)
            low_bound = (score * 0.7) if score != 1.0 else 1.0

            close_skills = [
                skill for skill, conf in skill_confs.items()
                if conf >= low_bound and skill != best_skill
            ]
            if close_skills:
                raise MultipleSkillMatches([best_skill] + close_skills)
            return best_skill
