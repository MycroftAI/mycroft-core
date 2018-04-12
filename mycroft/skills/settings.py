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
    SkillSettings is a simple extension of a Python dict which enables
    simplified storage of settings.  Values stored into the dict will
    automatically persist locally.  Additionally, it can interact with
    a backend system to provide a GUI interface for some or all of the
    settings.

    The GUI for the setting is described by a file in the skill's root
    directory called settingsmeta.json.  The "name" is associates the
    user-interface field with the setting name in the dictionary.  For
    example, you might have a setting['username'].  In the settingsmeta
    you can describe the interface you want to edit that value with:
        ...
        "fields": [
               {
                   "name": "username",
                   "type": "email",
                   "label": "Email address to associate",
                   "placeholder": "example@mail.com",
                   "value": ""
               }]
        ...
    When the user changes the setting via the web UI, it will be sent
    down to all the devices and automatically placed into the
    settings['username'].  Any local changes made to the value (e.g.
    via a verbal interaction) will also be synched to the server to show
    on the web interface.

    NOTE: As it stands today, this functions seamlessly with a single
    device.  With multiple devices there are a few hitches that are being
    worked out.  The first device where a skill is installed creates the
    setting and values are sent down to any other devices that install the
    same skill.  However only the original device can make changes locally
    for synching to the web.  This limitation is temporary and will be
    removed soon.


    Usage Example:
        from mycroft.skill.settings import SkillSettings

        s = SkillSettings('./settings.json', 'ImportantSettings')
        s['meaning of life'] = 42
        s['flower pot sayings'] = 'Not again...'
        s.store()  # This happens automagically in a MycroftSkill
"""

import json
import hashlib
from threading import Timer
from os.path import isfile, join, expanduser, basename

from mycroft.api import DeviceApi, is_paired
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
        # when skills try to instantiate settings
        # in __init__, it can erase the settings saved
        # on disk (settings.json). So this prevents that
        # This is set to true in core.py after skill init
        self.allow_overwrite = False

        self.api = DeviceApi()
        self.config = ConfigurationManager.get()
        self.name = name
        self.directory = directory
        # set file paths
        self._settings_path = join(directory, 'settings.json')
        self._meta_path = join(directory, 'settingsmeta.json')
        self.loaded_hash = hash(str(self))
        self._complete_intialization = False
        self._device_identity = None
        self._api_path = None
        self._user_identity = None
        self.changed_callback = None
        self._poll_timer = None
        self._is_alive = True

        # if settingsmeta exist
        if isfile(self._meta_path):
            self._poll_skill_settings()

    def run_poll(self, _=None):
        """Immediately poll the web for new skill settings"""
        if self._poll_timer:
            self._poll_timer.cancel()
            self._poll_skill_settings()

    def stop_polling(self):
        self._is_alive = False
        if self._poll_timer:
            self._poll_timer.cancel()

    def set_changed_callback(self, callback):
        """
            Set callback to perform when server settings have changed.

            callback: function/method to call when settings have changed
        """
        self.changed_callback = callback

    # TODO: break this up into two classes
    def initialize_remote_settings(self):
        """ initializes the remote settings to the server """
        # if settingsmeta.json exists (and is valid)
        # this block of code is a control flow for
        # different scenarios that may arises with settingsmeta
        self.load_skill_settings_from_file()  # loads existing settings.json
        settings_meta = self._load_settings_meta()
        if not settings_meta:
            return

        if not is_paired():
            return

        self._device_identity = self.api.identity.uuid
        self._api_path = "/" + self._device_identity + "/skill"
        self._user_identity = self.api.get()['user']['uuid']
        LOG.debug("settingsmeta.json exist for {}".format(self.name))
        hashed_meta = self._get_meta_hash(str(settings_meta))
        skill_settings = self._request_other_settings(hashed_meta)
        # if hash is new then there is a diff version of settingsmeta
        if self._is_new_hash(hashed_meta):
            # first look at all other devices on user account to see
            # if the settings exist. if it does then sync with device
            if skill_settings:
                # not_owner flags that this settings is loaded from
                # another device. If a skill settings doesn't have
                # not_owner, then the skill is created from that device
                self['not_owner'] = True
                self.save_skill_settings(skill_settings)
            else:  # upload skill settings if
                uuid = self._load_uuid()
                if uuid is not None:
                    self._delete_metadata(uuid)
                self._upload_meta(settings_meta, hashed_meta)
        else:  # hash is not new
            if skill_settings is not None:
                self['not_owner'] = True
                self.save_skill_settings(skill_settings)
            else:
                settings = self._request_my_settings(hashed_meta)
                if settings is None:
                    LOG.debug("seems like it got deleted from home... "
                              "sending settingsmeta.json for "
                              "{}".format(self.name))
                    self._upload_meta(settings_meta, hashed_meta)
                else:
                    self.save_skill_settings(settings)
        self._complete_intialization = True

    @property
    def _is_stored(self):
        return hash(str(self)) == self.loaded_hash

    def __getitem__(self, key):
        """ Get key """
        return super(SkillSettings, self).__getitem__(key)

    def __setitem__(self, key, value):
        """ Add/Update key. """
        if self.allow_overwrite or key not in self:
            return super(SkillSettings, self).__setitem__(key, value)

    def _load_settings_meta(self):
        """ Loads settings metadata from skills path. """
        if isfile(self._meta_path):
            try:
                with open(self._meta_path) as f:
                    data = json.load(f)
                return data
            except Exception as e:
                LOG.error("Failed to load setting file: "+self._meta_path)
                LOG.error(repr(e))
                return None
        else:
            LOG.debug("settingemeta.json does not exist")
            return None

    def _send_settings_meta(self, settings_meta):
        """ Send settingsmeta.json to the server.

            Args:
                settings_meta (dict): dictionary of the current settings meta

            Returns:
                str: uuid, a unique id for the setting meta data
        """
        try:
            uuid = self._put_metadata(settings_meta)
            return uuid
        except Exception as e:
            LOG.error(e)
            return None

    def save_skill_settings(self, skill_settings):
        """ takes skill object and save onto self

            Args:
                settings (dict): skill
        """
        if self._is_new_hash(skill_settings['identifier']):
            self._save_uuid(skill_settings['uuid'])
            self._save_hash(skill_settings['identifier'])
        sections = skill_settings['skillMetadata']['sections']
        for section in sections:
            for field in section["fields"]:
                if "name" in field and "value" in field:
                    self[field['name']] = field['value']
        self.store()

    def _load_uuid(self):
        """ Loads uuid

            Returns:
                str: uuid of the previous settingsmeta
        """
        directory = self.config.get("skills")["directory"]
        directory = join(directory, self.name)
        directory = expanduser(directory)
        uuid_file = join(directory, 'uuid')
        uuid = None
        if isfile(uuid_file):
            with open(uuid_file, 'r') as f:
                uuid = f.read()
        return uuid

    def _save_uuid(self, uuid):
        """ Saves uuid.

            Args:
                str: uuid, unique id of new settingsmeta
        """
        LOG.debug("saving uuid {}".format(str(uuid)))
        directory = self.config.get("skills")["directory"]
        directory = join(directory, self.name)
        directory = expanduser(directory)
        uuid_file = join(directory, 'uuid')
        with open(uuid_file, 'w') as f:
            f.write(str(uuid))

    def _uuid_exist(self):
        """ Checks if there is an uuid file.

            Returns:
                bool: True if uuid file exist False otherwise
        """
        directory = self.config.get("skills")["directory"]
        directory = join(directory, self.name)
        directory = expanduser(directory)
        uuid_file = join(directory, 'uuid')
        return isfile(uuid_file)

    def _migrate_settings(self, settings_meta):
        """ sync settings.json and settingsmeta.json in memory """
        meta = settings_meta.copy()
        self.load_skill_settings_from_file()
        sections = meta['skillMetadata']['sections']
        for i, section in enumerate(sections):
            for j, field in enumerate(section['fields']):
                if 'name' in field:
                    if field["name"] in self:
                        sections[i]['fields'][j]['value'] = \
                            str(self.__getitem__(field['name']))
        meta['skillMetadata']['sections'] = sections
        return meta

    def _upload_meta(self, settings_meta, hashed_meta):
        """ uploads the new meta data to settings with settings migration

            Args:
                settings_meta (dict): settingsmeta.json
                hashed_meta (str): {skill-folder}-settinsmeta.json
        """
        LOG.debug("sending settingsmeta.json for {}".format(self.name) +
                  " to servers")
        meta = self._migrate_settings(settings_meta)
        meta['identifier'] = str(hashed_meta)
        response = self._send_settings_meta(meta)
        if response:
            self._save_uuid(response['uuid'])
            if 'not_owner' in self:
                del self['not_owner']
        self._save_hash(hashed_meta)

    def hash(self, str):
        """ md5 hasher for consistency across cpu architectures """
        return hashlib.md5(str).hexdigest()

    def _get_meta_hash(self, settings_meta):
        """ Get's the hash of skill

            Args:
                settings_meta (str): stringified settingsmeta

            Returns:
                _hash (str): hashed to identify skills
        """
        _hash = self.hash(str(settings_meta) + str(self._user_identity))
        return "{}--{}".format(basename(self.directory), _hash)

    def _save_hash(self, hashed_meta):
        """ Saves hashed_meta to settings directory.

            Args:
                hashed_meta (int): hash of new settingsmeta
        """
        LOG.debug("saving hash {}".format(str(hashed_meta)))
        directory = self.config.get("skills")["directory"]
        directory = join(directory, self.name)
        directory = expanduser(directory)
        hash_file = join(directory, 'hash')
        with open(hash_file, 'w') as f:
            f.write(str(hashed_meta))

    def _is_new_hash(self, hashed_meta):
        """ checks if the stored hash is the same as current.
            if the hashed file does not exist, usually in the
            case of first load, then the create it and return True

            Args:
                hashed_meta (int): hash of metadata and uuid of device

            Returns:
                bool: True if hash is new, otherwise False
        """
        directory = self.config.get("skills")["directory"]
        directory = join(directory, self.name)
        directory = expanduser(directory)
        hash_file = join(directory, 'hash')
        if isfile(hash_file):
            with open(hash_file, 'r') as f:
                current_hash = f.read()
            return False if current_hash == str(hashed_meta) else True
        return True

    def update_remote(self):
        """ update settings state from server """
        skills_settings = None
        settings_meta = self._load_settings_meta()
        if settings_meta is None:
            return
        hashed_meta = self._get_meta_hash(settings_meta)
        if self.get('not_owner'):
            skills_settings = self._request_other_settings(hashed_meta)
        if not skills_settings:
            skills_settings = self._request_my_settings(hashed_meta)

        if skills_settings is not None:
            self.save_skill_settings(skills_settings)
            self.store()
        else:
            settings_meta = self._load_settings_meta()
            self._upload_meta(settings_meta, hashed_meta)

    def _poll_skill_settings(self):
        """ If identifier exists for this skill poll to backend to
            request settings and store it if it changes
            TODO: implement as websocket

            Args:
                hashed_meta (int): the hashed identifier
        """
        original = hash(str(self))
        try:
            if not is_paired():
                pass
            elif not self._complete_intialization:
                self.initialize_remote_settings()
                if not self._complete_intialization:
                    return  # unable to do remote sync
            else:
                self.update_remote()

        except Exception as e:
            LOG.error('Failed to fetch skill settings:\n{}'.format(e))
        finally:
            # Call callback for updated settings
            if self.changed_callback and hash(str(self)) != original:
                self.changed_callback()

        if self._poll_timer:
            self._poll_timer.cancel()

        if not self._is_alive:
            return

        # continues to poll settings every minute
        self._poll_timer = Timer(60, self._poll_skill_settings)
        self._poll_timer.daemon = True
        self._poll_timer.start()

    def load_skill_settings_from_file(self):
        """ If settings.json exist, open and read stored values into self """
        if isfile(self._settings_path):
            with open(self._settings_path) as f:
                try:
                    json_data = json.load(f)
                    for key in json_data:
                        self[key] = json_data[key]
                except Exception as e:
                    # TODO: Show error on webUI.  Dev will have to fix
                    # metadata to be able to edit later.
                    LOG.error(e)

    def _request_my_settings(self, identifier):
        """ Get skill settings for this device associated
            with the identifier

            Args:
                identifier (str): a hashed_meta

            Returns:
                skill_settings (dict or None): returns a dict if matches
        """
        LOG.debug("getting skill settings from "
                  "server for {}".format(self.name))
        settings = self._request_settings()
        # this loads the settings into memory for use in self.store
        for skill_settings in settings:
            if skill_settings['identifier'] == identifier:
                self._remote_settings = skill_settings
                return skill_settings
        return None

    def _request_settings(self):
        """ Get all skill settings for this device from server.

            Returns:
                dict: dictionary with settings collected from the server.
        """
        settings = self.api.request({
            "method": "GET",
            "path": self._api_path
        })
        settings = [skills for skills in settings if skills is not None]
        return settings

    def _request_other_settings(self, identifier):
        """ Retrieves user skill from other devices by identifier (hashed_meta)

        Args:
            indentifier (str): identifier for this skill

        Returns:
            settings (dict or None): returns the settings if true else None
        """
        LOG.debug(
            "syncing settings with other devices "
            "from server for {}".format(self.name))

        path = \
            "/" + self._device_identity + "/userSkill?identifier=" + identifier
        user_skill = self.api.request({
            "method": "GET",
            "path": path
        })
        if len(user_skill) == 0:
            return None
        else:
            return user_skill[0]

    def _put_metadata(self, settings_meta):
        """ PUT settingsmeta to backend to be configured in server.
            used in place of POST and PATCH.

            Args:
                settings_meta (dict): dictionary of the current settings meta
                                      data
        """
        return self.api.request({
            "method": "PUT",
            "path": self._api_path,
            "json": settings_meta
        })

    def _delete_metadata(self, uuid):
        """ Deletes the current skill metadata

            Args:
                uuid (str): unique id of the skill
        """
        try:
            LOG.debug("deleting metadata")
            self.api.request({
                "method": "DELETE",
                "path": self._api_path + "/{}".format(uuid)
            })
        except Exception as e:
            LOG.error(e)
            LOG.error(
                "cannot delete metadata because this"
                "device is not original uploader of skill")

    @property
    def _should_upload_from_change(self):
        changed = False
        if hasattr(self, '_remote_settings'):
            sections = self._remote_settings['skillMetadata']['sections']
            for i, section in enumerate(sections):
                for j, field in enumerate(section['fields']):
                    if 'name' in field:
                        # Ensure that the field exists in settings and that
                        # it has a value to compare
                        if (field["name"] in self and
                                'value' in sections[i]['fields'][j]):
                            remote_val = sections[i]['fields'][j]["value"]
                            self_val = self.get(field['name'])
                            if str(remote_val) != str(self_val):
                                changed = True
        if self.get('not_owner'):
            changed = False
        return changed

    def store(self, force=False):
        """ Store dictionary to file if a change has occured.

            Args:
                force:  Force write despite no change
        """

        if force or not self._is_stored:
            with open(self._settings_path, 'w') as f:
                json.dump(self, f)
            self.loaded_hash = hash(str(self))

        if self._should_upload_from_change:
            settings_meta = self._load_settings_meta()
            hashed_meta = self._get_meta_hash(settings_meta)
            uuid = self._load_uuid()
            if uuid is not None:
                LOG.debug("deleting meta data for {}".format(self.name))
                self._delete_metadata(uuid)
            self._upload_meta(settings_meta, hashed_meta)
