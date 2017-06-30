# Copyright 2017 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

"""
    This module provides the SkillSettings dictionary, which is a simple
    extension of the python dict to enable storing.

    Example:
        from mycroft.skill.settings import SkillSettings

        s = SkillSettings('./settings.json')
        s['meaning of life'] = 42
        s['flower pot sayings'] = 'Not again...'
        s.store()
"""

import json
import sys
from threading import Timer
from os.path import isfile, join, exists, expanduser
from mycroft.util.log import getLogger
from mycroft.api import DeviceApi

logger = getLogger(__name__)
SKILLS_DIR = "/opt/mycroft/skills"


# TODO: account for settings changes through skill ie. change default playlist
class SkillSettings(dict):
    """
        SkillSettings creates a dictionary that can easily be stored
        to file, serialized as json. It also syncs to the backend for
        skill configuration

        Args:
            settings_file (str): Path to storage file
    """
    def __init__(self, directory, name):
        super(SkillSettings, self).__init__()
        self.api = DeviceApi()
        self.name = name
        self._device_identity = self.api.identity.uuid
        self._settings_path = join(directory, 'settings.json')
        self._meta_path = join(directory, 'settingsmeta.json')
        self._uuid_path = join(expanduser('~/.mycroft/skills/') + self.name,
                               'identity.json')
        self._api_path = "/" + self._device_identity + "/skill"
        self.loaded_hash = hash(str(self))

        self._send_settings_meta()
        self._poll_web_settings()
        self._load_web_settings()

    @property
    def _is_stored(self):
        return hash(str(self)) == self.loaded_hash

    def __getitem__(self, key):
        return super(SkillSettings, self).__getitem__(key)

    def __setitem__(self, key, value):
        """
            Add/Update key and note that the file needs saving.
        """
        return super(SkillSettings, self).__setitem__(key, value)

    def _send_settings_meta(self):
        """
            TODO: do a poll, if settingsmeta.json changes, PATCH it to backend
            If settings meta data exists and skill does not have a uuid,
            send settingsmeta.json to the backend and store uuid for skill
        """
        if isfile(self._meta_path):
            with open(self._meta_path) as f:
                self.settings_meta = json.load(f)

            # If skill is loaded for the first time post metadata
            # to backend and store uuid for skill
            if not isfile(self._uuid_path):
                response = self._post_metadata(self.settings_meta)
                self._store_uuid(response)

    def _poll_web_settings(self):
        """
            If uuid exists for this skill poll to backend to
            request settings and store it if it changes
            TODO: implement as websocket
        """
        if isfile(self._uuid_path):
            with open(self._uuid_path, 'r') as f:
                data = json.load(f)

            response = self._get_settings()

            for skill_setting in response:
                if skill_setting['uuid'] == data['uuid']:
                    settings_list = skill_setting['skillMetadata']['sections']
                    for section in settings_list:
                        for field in section["fields"]:
                            self.__setitem__(field["name"], field["value"])

            self.store()
            # poll backend every 60 seconds for new settings
            Timer(60, self._poll_web_settings).start()

    def _load_web_settings(self):
        """
            If settings.json exist, open and read stored values into self
        """
        if isfile(self._settings_path):
            with open(self._settings_path) as f:
                try:
                    json_data = json.load(f)
                    for key in json_data:
                        self.__setitem__(key, json_data[key])
                except Exception as e:
                    # TODO: Show error on webUI.  Dev will have to fix
                    # metadata to be able to edit later.
                    logger.error(e)

    def _store_uuid(self, uuid):
        """
            Store uuid as identity.json in ~/.mycroft/skills/{skillname}
        """
        with open(self._uuid_path, 'w') as f:
            json.dump(uuid, f)

    def _get_settings(self):
        """
            Goes to backend to get skill configurations for this device
        """
        return self.api.request({
            "method": "GET",
            "path": self._api_path
        })

    def _post_metadata(self, settings_meta):
        """
            POST settingsmeta to backend to be configured in home.mycroft.ai
        """
        return self.api.request({
            "method": "POST",
            "path": self._api_path,
            "json": settings_meta
        })

    def store(self):
        """
            Store dictionary to file if it has changed
        """
        if not self._is_stored:
            with open(self._settings_path, 'w') as f:
                json.dump(self, f)
            self.loaded_hash = hash(str(self))
