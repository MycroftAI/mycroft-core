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
import json
import os
from os.path import join, isfile, isdir
from json_database import JsonStorage

from mycroft.api import DeviceApi, is_paired
from mycroft.configuration import Configuration
from ovos_utils.configuration import get_xdg_data_save_path
from mycroft.util import connected
from combo_lock import ComboLock
from mycroft.util.log import LOG
from mycroft.util.file_utils import get_temp_path
from mycroft.skills.skill_loader import get_skill_directories


ONE_HOUR = 3600
FIVE_MINUTES = 300  # number of seconds in a minute


def skill_is_blacklisted(skill):
    """DEPRECATED: do not use, method only for api backwards compatibility
    Logs a warning and returns False
    """
    # this is a internal msm helper
    # it should have been private
    # cant remove to keep api compatibility
    # nothing in the wild should be using this
    LOG.warning("skill_is_blacklisted is an internal method and has been deprecated. Stop using it!")
    return False


class _SeleneSkillsManifest(JsonStorage):
    """dict subclass with save/load support

    This dictionary contains the metadata expected by selene backend
    This data is used to populate entries in selene skill settings page
    It is only uploaded if enabled in mycroft.conf and device is paired

    Direct usage is strongly discouraged, the purpose of this class is api backwards compatibility
    """
    def __init__(self, api=None):
        path = os.path.join(get_xdg_data_save_path(), 'skills.json')
        super().__init__(path)
        if "skills" not in self:
            self["skills"] = []
            self.store()
        self.api = api or DeviceApi()

    def device_skill_state_hash(self):
        return hash(json.dumps(self, sort_keys=True))

    def add_skill(self, skill_id):
        if self.api.identity.uuid:
            skill_gid = f'@{self.api.identity.uuid}|{skill_id}'
        else:
            skill_gid = f'@|{skill_id}'
        skill = {
            "name": skill_id,
            "origin": "non-msm",
            "beta": True,
            "status": 'active',
            "installed": 0,
            "updated": 0,
            "installation": 'installed',
            "skill_gid": skill_gid
        }
        if "skills" not in self:
            self["skills"] = []
        self["skills"].append(skill)

    def get_skill_state(self, skill_id):
        """Find a skill entry in the device skill state and returns it."""
        for skill_state in self.get('skills', []):
            if skill_state.get('name') == skill_id:
                return skill_state
        return {}

    def scan_skills(self):
        for directory in get_skill_directories():
            if not isdir(directory):
                continue
            for skill_id in os.listdir(directory):
                skill_init = join(directory, skill_id, "__init__.py")
                if isfile(skill_init):
                    self.add_skill(skill_id)
        self.store()


class SkillUpdater:
    """Class facilitating skill update / install actions.

    Arguments
        bus (MessageBusClient): Optional bus emitter Used to communicate
                                with the mycroft core system and handle
                                commands.
    """

    def __init__(self, bus=None):
        self.__skill_manifest = _SeleneSkillsManifest()
        self.post_manifest(True)

        self.installed_skills = set()

        # below are unused, only for api backwards compat
        self.msm_lock = ComboLock(get_temp_path('mycroft-msm.lck'))
        self.install_retries = 0
        self.config = Configuration.get()
        update_interval = self.config['skills'].get('update_interval', 1.0)
        self.update_interval = int(update_interval) * ONE_HOUR
        self.dot_msm_path = "/tmp/.msm"
        self.next_download = 0
        self.default_skill_install_error = False

        if bus:
            LOG.warning("bus argument has been deprecated")

    @property
    def installed_skills_file_path(self):
        """Property representing the path of the installed skills file."""
        return self.__skill_manifest.path

    @property
    def msm(self):
        """DEPRECATED: do not use, method only for api backwards compatibility
        Logs a warning and returns None
        """
        # unused but need to keep api backwards compatible
        # log a warning and move on
        LOG.warning("msm has been deprecated\n"
                    "DO NOT use self.msm property")
        return None

    @property
    def default_skill_names(self) -> tuple:
        """Property representing the default skills expected to be installed"""
        LOG.warning("msm has been deprecated\n"
                    "skill install/update is no longer handled by ovos-core")
        return ()

    def update_skills(self, quick=False):
        """DEPRECATED: do not use, method only for api backwards compatibility
        Logs a warning and returns True
        """
        LOG.warning("msm has been deprecated\n"
                    "skill install/update is no longer handled by ovos-core")
        return True

    def handle_not_connected(self):
        """"DEPRECATED: do not use, method only for api backwards compatibility
        Logs a warning
        """
        LOG.warning("msm has been deprecated\n"
                    "no update will be scheduled")

    def post_manifest(self, reload_skills_manifest=False):
        """Post the manifest of the device's skills to the backend."""
        upload_allowed = Configuration.get()['skills'].get('upload_skill_manifest')
        if upload_allowed and is_paired():
            if reload_skills_manifest:
                self.__skill_manifest.clear()
                self.__skill_manifest.scan_skills()
            try:
                device_api = DeviceApi()
                device_api.upload_skills_data(self.__skill_manifest)
            except Exception:
                LOG.error('Could not upload skill manifest')

    def install_or_update(self, skill):
        """DEPRECATED: do not use, method only for api backwards compatibility
        Logs a warning
        """
        LOG.warning("msm has been deprecated\n"
                    f"{skill} will not be changed")

    def defaults_installed(self):
        """DEPRECATED: do not use, method only for api backwards compatibility
        Logs a warning and returns True
        """
        LOG.warning("msm has been deprecated\n"
                    "skill install/update is no longer handled by ovos-core")
        return True
