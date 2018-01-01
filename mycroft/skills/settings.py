# Copyright 2017 Mycroft AI Inc.
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
"""
    SkillSettings is a simple extension of the python dict which enables
    local storage of settings.  Additionally it can interact with a backend
    system to provide a GUI interface, described by meta-data described in
    an optional 'settingsmeta.json' file.

    Usage Example:
        from mycroft.skill.settings import SkillSettings

        s = SkillSettings('./settings.json', 'ImportantSettings')
        s['meaning of life'] = 42
        s['flower pot sayings'] = 'Not again...'
        s.store()

    Metadata format:
        TODO: see https://goo.gl/MY3i1S
"""

import json
from threading import Timer
from os.path import isfile, join, expanduser

from mycroft.api import DeviceApi
from mycroft.util.log import LOG
from mycroft.configuration import ConfigurationManager


class SkillSettings(dict):
    """ A dictionary that can easily be save to a file, serialized as json. It
        also syncs to the backend for skill settings

        Args:
            directory (str): Path to storage directory
            name (str):      user readable name associated with the settings
    """

    def __init__(self, directory, name):
        super(SkillSettings, self).__init__()
        self.api = DeviceApi()
        # self._device_identity = self.api.identity.uuid
        self.config = ConfigurationManager.get()
        self.name = name
        # set file paths
        self._settings_path = join(directory, 'settings.json')
        # self._meta_path = join(directory, 'settingsmeta.json')
        #self._api_path = "/" + self._device_identity + "/skill"
        self.is_alive = True
        self.loaded_hash = hash(str(self))

        # if settingsmeta.json exists
        # this block of code is a control flow for
        # different scenarios that may arises with settingsmeta
        # if isfile(self._meta_path):
        #    LOG.info("settingsmeta.json exist for {}".format(self.name))
        #    settings_meta = self._load_settings_meta()
        #   hashed_meta = hash(str(settings_meta) + str(
        # self._device_identity))
            # check if hash is different from the saved hashed
        #    if self._is_new_hash(hashed_meta):
        #        LOG.info("looks like settingsmeta.json " +
        #                 "has changed for {}".format(self.name))
                # TODO: once the delete api for device is created uncomment
        #        if self._uuid_exist():
        #            try:
        #                LOG.info("a uuid exist for {}".format(self.name) +
        #                         " deleting old one")
        #                old_uuid = self._load_uuid()
        #                self._delete_metatdata(old_uuid)
        #            except Exception as e:
        #                LOG.info(e)
        #        LOG.info("sending settingsmeta.json for {}".format(
        ## self.name) +
        #                 " to home.mycroft.ai")
        #        new_uuid = self._send_settings_meta(settings_meta,
        # hashed_meta)
        #        self._save_uuid(new_uuid)
        #        self._save_hash(hashed_meta)
        #    else:  # if hash is old
        #        found_in_backend = False
        #        settings = self._get_remote_settings()
                # checks backend if the settings have been deleted via webUI
        #        for skill in settings:
        #            if skill["identifier"] == str(hashed_meta):
        #                found_in_backend = True
                # if it's been deleted from webUI resend
        #        if found_in_backend is False:
        #            LOG.info("seems like it got deleted from home... " +
        #                     "sending settingsmeta.json for " +
        #                     "{}".format(self.name))
        #            new_uuid = self._send_settings_meta(
        #                settings_meta, hashed_meta)
        #            self._save_uuid(new_uuid)
        #            self._save_hash(hashed_meta)

        #   t = Timer(60, self._poll_skill_settings, [hashed_meta])
        #   t.daemon = True
        #   t.start()

        self.load_skill_settings()

    def load_skill_settings_from_file(self):
        self.load_skill_settings()

    @property
    def _is_stored(self):
        return hash(str(self)) == self.loaded_hash

    def __getitem__(self, key):
        """ Get key """
        return super(SkillSettings, self).__getitem__(key)

    def __setitem__(self, key, value):
        """ Add/Update key. """
        return super(SkillSettings, self).__setitem__(key, value)

    def _load_settings_meta(self):
        """ Loads settings metadata from skills path. """
        # with open(self._meta_path) as f:
        #    data = json.load(f)
        # return data
        return {}

    def _send_settings_meta(self, settings_meta, hashed_meta):
        """ Send settingsmeta.json to the backend.

            Args:
                settings_meta (dict): dictionary of the current settings meta
                                      data
                hased_meta (int): hash value for settings meta data

            Returns:
                str: uuid, a unique id for the setting meta data
        """
        # try:
        #    settings_meta["identifier"] = str(hashed_meta)
        #    self._put_metadata(settings_meta)
        #    settings = self._get_remote_settings()
        #    skill_identity = str(hashed_meta)
        #    uuid = None
        #    # TODO: note uuid should be returned from the put request
        #    for skill_setting in settings:
        #        if skill_setting['identifier'] == skill_identity:
        #            uuid = skill_setting["uuid"]
        #    return uuid
        # except Exception as e:
        #    LOG.error(e)
        return None

    def _load_uuid(self):
        """ Loads uuid

            Returns:
                str: uuid of the previous settingsmeta
        """
        # directory = self.config.get("skills")["directory"]
        # directory = join(directory, self.name)
        # directory = expanduser(directory)
        # uuid_file = join(directory, 'uuid')
        # if isfile(uuid_file):
        #    with open(uuid_file, 'r') as f:
        #        uuid = f.read()
        # return uuid
        return None

    def _save_uuid(self, uuid):
        """ Saves uuid to the settings directory.

            Args:
                str: uuid, unique id of new settingsmeta
        """
        LOG.info("saving uuid {}".format(str(uuid)))
        # directory = self.config.get("skills")["directory"]
        # directory = join(directory, self.name)
        # directory = expanduser(directory)
        # uuid_file = join(directory, 'uuid')
        # with open(uuid_file, 'w') as f:
        #    f.write(str(uuid))

    def _save_hash(self, hashed_meta):
        """ Saves hashed_meta to settings directory.

            Args:
                hashed_meta (int): hash of new settingsmeta
        """
        LOG.info("saving hash {}".format(str(hashed_meta)))
        # directory = self.config.get("skills")["directory"]
        # directory = join(directory, self.name)
        # directory = expanduser(directory)
        # hash_file = join(directory, 'hash')
        # with open(hash_file, 'w') as f:
        #    f.write(str(hashed_meta))

    def _uuid_exist(self):
        """ Checks if there is an uuid file.

            Returns:
                bool: True if uuid file exist False otherwise
        """
        # directory = self.config.get("skills")["directory"]
        # directory = join(directory, self.name)
        # directory = expanduser(directory)
        # uuid_file = join(directory, 'uuid')
        #return isfile(uuid_file)
        return True

    def _is_new_hash(self, hashed_meta):
        """ checks if the stored hash is the same as current.
            if the hashed file does not exist, usually in the
            case of first load, then the create it and return True

            Args:
                hashed_meta (int): hash of metadata and uuid of device

            Returns:
                bool: True if hash is new, otherwise False
        """
        # directory = self.config.get("skills")["directory"]
        # directory = join(directory, self.name)
        # directory = expanduser(directory)
        # hash_file = join(directory, 'hash')
        # if isfile(hash_file):
        #    with open(hash_file, 'r') as f:
        #        current_hash = f.read()
        #    return False if current_hash == str(hashed_meta) else True
        #return True
        return False

    def _poll_skill_settings(self, hashed_meta):
        """ If identifier exists for this skill poll to backend to
            request settings and store it if it changes
            TODO: implement as websocket

            Args:
                hashed_meta (int): the hashed identifier
        """
        LOG.info("getting settings from home.mycroft.ai")
        #try:
        # update settings
        #    settings = self._get_remote_settings()
        #    skill_identity = str(hashed_meta)
        #    for skill_setting in settings:
        #        if skill_setting['identifier'] == skill_identity:
        #            sections = skill_setting['skillMetadata']['sections']
        #            for section in sections:
        #                for field in section["fields"]:
        #                    self.__setitem__(field["name"], field["value"])

            # store value if settings has changed from backend
        #    self.store()

        # except Exception as e:
        #    LOG.error(e)

        # if self.is_alive:
        #    # continues to poll settings every 60 seconds
        #    t = Timer(60, self._poll_skill_settings, [hashed_meta])
        #    t.daemon = True
        #    t.start()

    def load_skill_settings(self):
        """ If settings.json exist, open and read stored values into self """
        if isfile(self._settings_path):
            with open(self._settings_path) as f:
                try:
                    json_data = json.load(f)
                    for key in json_data:
                        self.__setitem__(key, json_data[key])
                except Exception as e:
                    # TODO: Show error on webUI.  Dev will have to fix
                    # metadata to be able to edit later.
                    LOG.error(e)

    def _get_remote_settings(self):
        """ Get skill settings for this device from backend.

            Returns:
                dict: dictionary with settings collected from the web backend.
        """
        # settings = self.api.request({
        #    "method": "GET",
        #    "path": self._api_path
        # })
        # settings = [skills for skills in settings if skills is not None]
        #return settings
        return []

    def _put_metadata(self, settings_meta):
        """ PUT settingsmeta to backend to be configured in home.mycroft.ai.
            used in place of POST and PATCH.

            Args:
                settings_meta (dict): dictionary of the current settings meta
                                      data
        """
        # return self.api.request({
        #    "method": "PUT",
        #   "path": self._api_path,
        #    "json": settings_meta
        #})
        return None

    def _delete_metatdata(self, uuid):
        """ Deletes the current skill metadata

            Args:
                uuid (str): unique id of the skill
        """
        # return self.api.request({
        #    "method": "DELETE",
        #    "path": self._api_path + "/{}".format(uuid)
        #})
        return None

    def store(self, force=False):
        """ Store dictionary to file if a change has occured.

            Args:
                force:  Force write despite no change
        """
        if force or not self._is_stored:
            with open(self._settings_path, 'w') as f:
                json.dump(self, f)
            self.loaded_hash = hash(str(self))
