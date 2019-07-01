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
    directory called settingsmeta.json (or settingsmeta.yaml, if you
    prefer working with yaml). The "name" associates the user-interface
    field with the setting name in the dictionary. For example, you
    might have a setting['username'].  In the settingsmeta you can
    describe the interface you want to edit that value with:
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
import os
import yaml
import time
import copy
import re
from threading import Timer
from os.path import isfile, join, expanduser
from requests.exceptions import RequestException, HTTPError
from msm import SkillEntry

from mycroft.api import DeviceApi, is_paired
from mycroft.util.log import LOG
from mycroft.util import camel_case_split
from mycroft.configuration import ConfigurationManager

from .msm_wrapper import create_msm


msm = None
msm_creation_time = 0


def build_global_id(directory, config):
    """ Create global id for the skill.

    TODO: Handle dirty skill

    Arguments:
        directory:  skill directory
        config:     config for the device to fetch msm setup
     """
    # Update the msm object if it's more than an hour old
    global msm
    global msm_creation_time
    if msm is None or time.time() - msm_creation_time > 60 * 60:
        msm_creation_time = time.time()
        msm = create_msm(config)

    s = SkillEntry.from_folder(directory, msm)
    # If modified prepend the device uuid
    return s.skill_gid, s.meta_info.get('display_name')


def display_name(name):
    """ Splits camelcase and removes leading/trailing Skill. """
    name = re.sub(r'(^[Ss]kill|[Ss]kill$)', '', name)
    return camel_case_split(name)


class DelayRequest(Exception):
    """ Indicate that the next request should be delayed. """
    pass


class SkillSettings(dict):
    """ Dictionary that can easily be saved to a file, serialized as json. It
        also syncs to the backend for skill settings

    Args:
        directory (str):  Path to storage directory
        name (str):       user readable name associated with the settings
        no_upload (bool): True if the upload to mycroft servers should be
                          disabled.
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
        # set file paths
        self._settings_path = join(directory, 'settings.json')
        self._meta_path = _get_meta_path(directory)
        self._directory = directory

        self.is_alive = True
        self.loaded_hash = hash(json.dumps(self, sort_keys=True))
        self._complete_intialization = False
        self._device_identity = None
        self._api_path = None
        self._user_identity = None
        self.changed_callback = None
        self._poll_timer = None
        self._blank_poll_timer = None
        self._is_alive = True

        # Add Information extracted from the skills-meta.json entry for the
        # skill.
        skill_gid, disp_name = build_global_id(self._directory, self.config)
        self.__skill_gid = skill_gid
        self.display_name = disp_name

        # if settingsmeta exist
        if self._meta_path:
            self._poll_skill_settings()
        # if not disallowed by user upload an entry for all skills installed
        elif self.config['skills']['upload_skill_manifest']:
            self._blank_poll_timer = Timer(1, self._init_blank_meta)
            self._blank_poll_timer.daemon = True
            self._blank_poll_timer.start()

    @property
    def skill_gid(self):
        """ Finalizes the skill gid to include device uuid if needed. """
        if is_paired():
            return self.__skill_gid.replace('@|', '@{}|'.format(
                DeviceApi().identity.uuid))
        else:
            return self.__skill_gid

    def __hash__(self):
        """ Simple object unique hash. """
        return hash(str(id(self)) + self.name)

    def run_poll(self, _=None):
        """Immediately poll the web for new skill settings"""
        if self._poll_timer:
            self._poll_timer.cancel()
            self._poll_skill_settings()

    def stop_polling(self):
        self._is_alive = False
        if self._poll_timer:
            self._poll_timer.cancel()
        if self._blank_poll_timer:
            self._blank_poll_timer.cancel()

    def set_changed_callback(self, callback):
        """ Set callback to perform when server settings have changed.

        Args:
            callback: function/method to call when settings have changed
        """
        self.changed_callback = callback

    # TODO: break this up into two classes
    def initialize_remote_settings(self):
        """ initializes the remote settings to the server """
        # if the settingsmeta file exists (and is valid)
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
        try:
            self._user_identity = self.api.get()['user']['uuid']
        except RequestException:
            return

        settings = self._request_my_settings(self.skill_gid)
        if settings:
            self.save_skill_settings(settings)

        # TODO if this skill_gid is not a modified version check if a modified
        # version exists on the server and delete it

        # Always try to upload settingsmeta on startup
        self._upload_meta(settings_meta, self.skill_gid)

        self._complete_intialization = True

    @property
    def _is_stored(self):
        return hash(json.dumps(self, sort_keys=True)) == self.loaded_hash

    def __getitem__(self, key):
        """ Get key """
        return super(SkillSettings, self).__getitem__(key)

    def __setitem__(self, key, value):
        """ Add/Update key. """
        if self.allow_overwrite or key not in self:
            return super(SkillSettings, self).__setitem__(key, value)

    def _load_settings_meta(self):
        """ Load settings metadata from the skill folder.

        If no settingsmeta exists a basic settingsmeta will be created
        containing a basic identifier.

        Returns:
            (dict) settings meta
        """
        if self._meta_path and os.path.isfile(self._meta_path):
            _, ext = os.path.splitext(self._meta_path)
            json_file = True if ext.lower() == ".json" else False

            try:
                with open(self._meta_path, encoding='utf-8') as f:
                    if json_file:
                        data = json.load(f)
                    else:
                        data = yaml.safe_load(f)
            except Exception as e:
                LOG.error("Failed to load setting file: " + self._meta_path)
                LOG.error(repr(e))
                data = {}
        else:
            data = {}

        # Insert skill_gid and display_name
        data['skill_gid'] = self.skill_gid
        data['display_name'] = (self.display_name or data.get('name') or
                                display_name(self.name))

        # Backwards compatibility:
        if 'name' not in data:
            data['name'] = data['display_name']

        return data

    def _send_settings_meta(self, settings_meta):
        """ Send settingsmeta to the server.

        Args:
            settings_meta (dict): dictionary of the current settings meta
        Returns:
            dict: uuid, a unique id for the setting meta data
        """
        try:
            uuid = self.api.upload_skill_metadata(
                self._type_cast(settings_meta, to_platform='web'))
            return uuid
        except HTTPError as e:
            if e.response.status_code in [422, 500, 501]:
                LOG.info(e.response.status_code)
                raise DelayRequest
            else:
                LOG.error(e)
                return None

        except Exception as e:
            LOG.error(e)
            return None

    def save_skill_settings(self, skill_settings):
        """ Takes skill object and save onto self

        Args:
            skill_settings (dict): skill
        """
        if 'skillMetadata' in skill_settings:
            sections = skill_settings['skillMetadata']['sections']
            for section in sections:
                for field in section["fields"]:
                    if "name" in field and "value" in field:
                        # Bypass the change lock to allow server to update
                        # during skill init
                        super(SkillSettings, self).__setitem__(field['name'],
                                                               field['value'])
            self.store()

    def _migrate_settings(self, settings_meta):
        """ sync settings.json and settingsmeta in memory """
        meta = settings_meta.copy()
        if 'skillMetadata' not in meta:
            return meta
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

    def _upload_meta(self, settings_meta, identifier):
        """ uploads the new meta data to settings with settings migration

        Args:
            settings_meta (dict): settingsmeta.json or settingsmeta.yaml
            identifier (str): identifier for skills meta data
        """
        LOG.debug('Uploading settings meta for {}'.format(identifier))
        meta = self._migrate_settings(settings_meta)
        meta['identifier'] = identifier
        response = self._send_settings_meta(meta)

    def hash(self, string):
        """ md5 hasher for consistency across cpu architectures """
        return hashlib.md5(bytes(string, 'utf-8')).hexdigest()

    def update_remote(self):
        """ update settings state from server """
        settings_meta = self._load_settings_meta()
        if settings_meta is None:
            return
        # Get settings
        skills_settings = self._request_my_settings(self.skill_gid)

        if skills_settings is not None:
            self.save_skill_settings(skills_settings)
        else:
            LOG.debug("No Settings on server for {}".format(self.skill_gid))
            # Settings meta doesn't exist on server push them
            settings_meta = self._load_settings_meta()
            self._upload_meta(settings_meta, self.skill_gid)

    def _init_blank_meta(self):
        """ Send blank settingsmeta to remote. """
        try:
            if not is_paired() and self.is_alive:
                self._blank_poll_timer = Timer(60, self._init_blank_meta)
                self._blank_poll_timer.daemon = True
                self._blank_poll_timer.start()
            else:
                self.initialize_remote_settings()
        except DelayRequest:
            # Delay 5 minutes and retry
            self._blank_poll_timer = Timer(60 * 5,
                                           self._init_blank_meta)
            self._blank_poll_timer.daemon = True
            self._blank_poll_timer.start()
        except Exception as e:
            LOG.exception('Failed to send blank meta: {}'.format(repr(e)))

    def _poll_skill_settings(self):
        """ If identifier exists for this skill poll to backend to
            request settings and store it if it changes
            TODO: implement as websocket
        """
        delay = 1
        original = hash(str(self))
        try:
            if not is_paired():
                pass
            elif not self._complete_intialization:
                self.initialize_remote_settings()
            else:
                self.update_remote()
        except DelayRequest:
            LOG.info('{}: Delaying next settings fetch'.format(self.name))
            delay = 5
        except Exception as e:
            LOG.exception('Failed to fetch skill settings: {}'.format(repr(e)))
        finally:
            # Call callback for updated settings
            if self._complete_intialization:
                if self.changed_callback and hash(str(self)) != original:
                    self.changed_callback()

        if self._poll_timer:
            self._poll_timer.cancel()

        if not self._is_alive:
            return

        # continues to poll settings every minute
        self._poll_timer = Timer(delay * 60, self._poll_skill_settings)
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

    def _type_cast(self, settings_meta, to_platform):
        """ Tranform data type to be compatible with Home and/or Core.

        e.g.
        Web to core
        "true" => True, "1.4" =>  1.4

        core to Web
        False => "false'

        Args:
            settings_meta (dict): skills object
            to_platform (str): platform to convert
                               compatible data types to
        Returns:
            dict: skills object
        """
        meta = settings_meta.copy()
        if 'skillMetadata' not in settings_meta:
            return meta

        sections = meta['skillMetadata']['sections']

        for i, section in enumerate(sections):
            for j, field in enumerate(section.get('fields', [])):
                _type = field.get('type')
                if _type == 'checkbox':
                    value = field.get('value')

                    if to_platform == 'web':
                        if value is True or value == 'True':
                            sections[i]['fields'][j]['value'] = 'true'
                        elif value is False or value == 'False':
                            sections[i]['fields'][j]['value'] = 'false'

                    elif to_platform == 'core':
                        if value == 'true' or value == 'True':
                            sections[i]['fields'][j]['value'] = True
                        elif value == 'false' or value == 'False':
                            sections[i]['fields'][j]['value'] = False

                elif _type == 'number':
                    value = field.get('value')

                    if to_platform == 'core':
                        if "." in value:
                            sections[i]['fields'][j]['value'] = float(value)
                        else:
                            sections[i]['fields'][j]['value'] = int(value)

                    elif to_platform == 'web':
                        sections[i]['fields'][j]['value'] = str(value)

        meta['skillMetadata']['sections'] = sections
        return meta

    def _request_my_settings(self, identifier):
        """ Get skill settings for this device associated
            with the identifier
        Args:
            identifier (str): a hashed_meta
        Returns:
            skill_settings (dict or None): returns a dict if matches
        """
        settings = self._request_settings()
        if settings:
            # this loads the settings into memory for use in self.store
            for skill_settings in settings:
                if skill_settings['identifier'] == identifier:
                    LOG.debug("Fetched settings for {}".format(identifier))
                    skill_settings = \
                        self._type_cast(skill_settings, to_platform='core')
                    self._remote_settings = skill_settings
                    return skill_settings
        return None

    def _request_settings(self):
        """ Get all skill settings for this device from server.

        Returns:
            dict: dictionary with settings collected from the server.
        """
        try:
            settings = self.api.get_skill_settings()
        except RequestException:
            return None

        settings = [skills for skills in settings if skills is not None]
        return settings

    @property
    def _should_upload_from_change(self):
        changed = False
        if (hasattr(self, '_remote_settings') and
                'skillMetadata' in self._remote_settings):
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
            self.loaded_hash = hash(json.dumps(self, sort_keys=True))

        if self._should_upload_from_change:
            settings_meta = self._load_settings_meta()
            self._upload_meta(settings_meta, self.skill_gid)


def _get_meta_path(base_directory):
    json_path = join(base_directory, 'settingsmeta.json')
    yaml_path = join(base_directory, 'settingsmeta.yaml')
    if isfile(json_path):
        return json_path
    if isfile(yaml_path):
        return yaml_path
    return None
