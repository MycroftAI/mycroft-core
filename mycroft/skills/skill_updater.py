# Copyright 2019 Mycroft AI Inc.
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
"""Periodically run by skill manager to update skills and post the manifest."""
import os
import sys
from datetime import datetime
from time import time

from msm import MsmException

from mycroft import dialog
from mycroft.api import DeviceApi, is_paired
from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util import connected
from mycroft.util.combo_lock import ComboLock
from mycroft.util.log import LOG
from .msm_wrapper import create_msm

ONE_HOUR = 3600
FIVE_MINUTES = 300  # number of seconds in a minute


class SkillUpdater:
    _installed_skills_file_path = None

    def __init__(self, bus):
        """Constructor

        Arguments
            bus (MessageBusClient): Used to communicate events to the bus.
        """
        self.bus = bus
        self.msm = create_msm(self.config)
        self.msm_lock = ComboLock('/tmp/mycroft-msm.lck')
        self.install_retries = 0
        update_interval = self.config['skills']['update_interval']
        self.update_interval = int(update_interval) * ONE_HOUR
        self.dot_msm_path = os.path.join(self.msm.skills_dir, '.msm')
        self.next_download = self._determine_next_download_time()
        self._log_next_download_time()
        self.installed_skills = set()
        self.default_skill_install_error = False

    def _determine_next_download_time(self):
        """Determine the initial values of the next/last download times.

        Update immediately if the .msm or installed skills file is missing
        otherwise use the timestamp on .msm as a basis.
        """
        msm_files_exist = (
                os.path.exists(self.dot_msm_path) and
                os.path.exists(self.installed_skills_file_path)
        )
        if msm_files_exist:
            mtime = os.path.getmtime(self.dot_msm_path)
            next_download = mtime + self.update_interval
        else:
            # Last update can't be found or the requirements don't seem to be
            # installed trigger update before skill loading
            next_download = time() - 1

        return next_download

    @property
    def config(self):
        """Property representing the device configuration."""
        return Configuration.get()

    @property
    def installed_skills_file_path(self):
        """Property representing the path of the installed skills file."""
        if self._installed_skills_file_path is None:
            virtual_env_path = os.path.dirname(os.path.dirname(sys.executable))
            if os.access(virtual_env_path, os.W_OK | os.R_OK | os.X_OK):
                self._installed_skills_file_path = os.path.join(
                    virtual_env_path,
                    '.mycroft-skills'
                )
            else:
                self._installed_skills_file_path = os.path.expanduser(
                    '~/.mycroft/.mycroft-skills'
                )

        return self._installed_skills_file_path

    @property
    def default_skill_names(self) -> tuple:
        """Property representing the default skills expected to be installed"""
        default_skill_groups = dict(self.msm.repo.get_default_skill_names())
        default_skills = set(default_skill_groups['default'])
        platform_default_skills = default_skill_groups.get(self.msm.platform)
        if platform_default_skills is None:
            log_msg = 'No default skills found for platform {}'
            LOG.info(log_msg.format(self.msm.platform))
        else:
            default_skills.update(platform_default_skills)

        return tuple(default_skills)

    def _load_installed_skills(self):
        """Load the last known skill listing from a file."""
        if os.path.isfile(self.installed_skills_file_path):
            with open(self.installed_skills_file_path) as skills_file:
                self.installed_skills = {
                    i.strip() for i in skills_file.readlines() if i.strip()
                }

    def _save_installed_skills(self):
        """Save the skill listing after the download to a file."""
        with open(self.installed_skills_file_path, 'w') as skills_file:
            for skill_name in self.installed_skills:
                skills_file.write(skill_name + '\n')

    def update_skills(self, speak=False, quick=False):
        """Invoke MSM to install default skills and/or update installed skills

        Args:
            speak (bool): Speak the result?
            quick (bool): Expedite the download by running with more threads?
        """
        LOG.info('Beginning skill update...')
        success = True
        if connected():
            self._load_installed_skills()
            with self.msm.lock:
                self._apply_install_or_update(quick)
            self._save_installed_skills()
            self._speak_skill_updated(speak)
            # Schedule retry in 5 minutes on failure, after 10 shorter periods
            # Go back to 60 minutes wait
            if self.default_skill_install_error and self.install_retries < 10:
                self._schedule_retry()
                success = False
            else:
                self.install_retries = 0
                self._update_download_time()
        else:
            self.handle_not_connected(speak)
            success = False

        if success:
            LOG.info('Skill update complete')

        return success

    def handle_not_connected(self, speak):
        """Notifications of the device not being connected to the internet"""
        LOG.error('msm failed, network connection not available')
        if speak:
            message = Message(
                "speak",
                dict(utterance=dialog.get('not connected to the internet'))
            )
            self.bus.emit(message)
        self.next_download = time() + FIVE_MINUTES

    def _apply_install_or_update(self, quick):
        """Invoke MSM to install or update a skill."""
        try:
            # Determine if all defaults are installed
            defaults = all(
                [s.is_local for s in self.msm.list_defaults()]
            )
            num_threads = 20 if not defaults or quick else 2
            self.msm.apply(
                self.install_or_update,
                self.msm.list(),
                max_threads=num_threads
            )
            self.post_manifest()

        except MsmException as e:
            LOG.error('Failed to update skills: {}'.format(repr(e)))

    def post_manifest(self):
        """Post the manifest of the device's skills to the backend."""
        upload_allowed = self.config['skills'].get('upload_skill_manifest')
        if upload_allowed and is_paired():
            try:
                device_api = DeviceApi()
                device_api.upload_skills_data(self.msm.skills_data)
            except Exception:
                LOG.exception('Could not upload skill manifest')

    def install_or_update(self, skill):
        """Install missing defaults and update existing skills"""
        if self._get_skill_data(skill.name).get('beta', False):
            skill.sha = None  # Will update to latest head
        if skill.is_local:
            skill.update()
            if skill.name not in self.installed_skills:
                skill.update_deps()
        elif skill.name in self.default_skill_names:
            try:
                self.msm.install(skill, origin='default')
            except Exception:
                if skill.name in self.default_skill_names:
                    LOG.warning(
                        'Failed to install default skill: ' + skill.name
                    )
                    self.default_skill_install_error = True
                raise
        self.installed_skills.add(skill.name)

    def _get_skill_data(self, skill_name):
        """Get skill data structure from name."""
        skill_data = {}
        for msm_skill_data in self.msm.skills_data.get('skills', []):
            if msm_skill_data.get('name') == skill_name:
                skill_data = msm_skill_data

        return skill_data

    def _speak_skill_updated(self, speak):
        """Emit a "speak" event to the bus to tell user skills updated."""
        if speak:
            data = {'utterance': dialog.get('skills updated')}
            self.bus.emit(Message('speak', data))

    def _schedule_retry(self):
        """Schedule the next skill update in the event of a failure."""
        self.install_retries += 1
        self.next_download = time() + FIVE_MINUTES
        self._log_next_download_time()
        self.default_skill_install_error = False

    def _update_download_time(self):
        """Update timestamp on .msm file to be used when system is restarted"""
        with open(self.dot_msm_path, 'a'):
            os.utime(self.dot_msm_path, None)
        self.next_download = time() + self.update_interval
        self._log_next_download_time()

    def _log_next_download_time(self):
        LOG.info(
            'Next scheduled skill update: ' +
            str(datetime.fromtimestamp(self.next_download))
        )