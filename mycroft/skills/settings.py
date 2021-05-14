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
"""Keep the settingsmeta.json and settings.json files in sync with the backend.

The SkillSettingsMeta and SkillSettings classes run a synchronization every
minute to ensure the device and the server have the same values.

The settingsmeta.json file (or settingsmeta.yaml, if you prefer working with
yaml) in the skill's root directory contains instructions for the Selene UI on
how to display and update a skill's settings, if there are any.

For example, you might have a setting named "username".  In the settingsmeta
you can describe the interface to edit that value with:
    ...
    "fields": [
        {
            "name": "username",
            "type": "email",
            "label": "Email address to associate",
            "placeholder": "example@mail.com",
            "value": ""
        }
    ]
    ...

When the user changes the setting via the web UI, it will be sent down to all
the devices related to an account and automatically placed into
settings['username'].  Any local changes made to the value (e.g. via a verbal
interaction) will also be synchronized to the server to show on the web
interface.

The settings.json file contains name/value pairs for each setting.  There can
be entries in settings.json that are not related to those the user can
manipulate on the web.  There is logic in the SkillSettings class to ensure
these "hidden" settings are not affected when the synchronization occurs.  A
skill can define a function that will be called when any settings change.

SkillSettings Usage Example:
    from mycroft.skill.settings import SkillSettings

        s = SkillSettings('./settings.json', 'ImportantSettings')
        s.skill_settings['meaning of life'] = 42
        s.skill_settings['flower pot sayings'] = 'Not again...'
        s.save_settings()  # This happens automagically in a MycroftSkill
"""
import json
import os
from os.path import dirname
import re
from pathlib import Path
from threading import Timer
from xdg.BaseDirectory import xdg_cache_home

import yaml

from mycroft.api import DeviceApi, is_paired, is_backend_disabled
from mycroft.configuration import Configuration, BASE_FOLDER
from mycroft.messagebus.message import Message
from mycroft.util import camel_case_split
from mycroft.util.log import LOG
from mycroft.util.file_utils import ensure_directory_exists
from mycroft.skills.msm_wrapper import build_msm_config, create_msm

ONE_MINUTE = 60


def get_local_settings(skill_dir, skill_name) -> dict:
    """Build a dictionary using the JSON string stored in settings.json."""
    skill_settings = {}
    settings_path = Path(skill_dir).joinpath('settings.json')
    LOG.info(settings_path)
    if settings_path.exists():
        with open(str(settings_path)) as settings_file:
            settings_file_content = settings_file.read()
        if settings_file_content:
            try:
                skill_settings = json.loads(settings_file_content)
            # TODO change to check for JSONDecodeError in 19.08
            except Exception:
                LOG.error(f'Failed to load {skill_name} settings from settings.json')

    return skill_settings


def save_settings(skill_dir, skill_settings):
    """Save skill settings to file."""
    settings_path = Path(skill_dir).joinpath('settings.json')

    # Either the file already exists or we are writing
    # to XDG_CONFIG_DIR and always have the permission to make
    # sure the file always exists
    if not Path(settings_path).exists():
        settings_path.touch(mode=0o644)

    with open(str(settings_path), 'w') as settings_file:
        try:
            json.dump(skill_settings, settings_file)
        except Exception:
            LOG.error(f'error saving skill settings to {settings_path}')
        else:
            LOG.info('Skill settings successfully saved to '
                     '{}' .format(settings_path))


def get_display_name(skill_name: str):
    """Splits camelcase and removes leading/trailing "skill"."""
    skill_name = re.sub(r'(^[Ss]kill|[Ss]kill$)', '', skill_name)
    return camel_case_split(skill_name)


class SettingsMetaUploader:
    """Synchronize the contents of the settingsmeta.json file with the backend.

    The settingsmeta.json (or settingsmeta.yaml) file is defined by the skill
    author.  It defines the user-configurable settings for a skill and contains
    instructions for how to display the skill's settings in the Selene web
    application (https://account.mycroft.ai).
    """
    _msm_skill_display_name = None
    _settings_meta_path = None

    def __init__(self, skill_directory: str, skill_name: str):
        self.skill_directory = Path(skill_directory)
        self.skill_name = skill_name
        self.json_path = self.skill_directory.joinpath('settingsmeta.json')
        self.yaml_path = self.skill_directory.joinpath('settingsmeta.yaml')
        self.config = Configuration.get()
        self.settings_meta = {}
        self.api = None
        self.upload_timer = None
        if is_backend_disabled():
            self.sync_enabled = False
        else:
            self.sync_enabled = self.config["server"]\
                .get("sync_skill_settings", False)
        if not self.sync_enabled:
            LOG.info("Skill settings sync is disabled, settingsmeta will "
                     "not be uploaded")

        self._stopped = None

        # Property placeholders
        self._msm = None
        self._skill_gid = None

    @property
    def msm(self):
        """Instance of the Mycroft Skills Manager"""
        if self._msm is None:
            msm_config = build_msm_config(self.config)
            self._msm = create_msm(msm_config)

        return self._msm

    def get_local_skills(self):
        """Generate a mapping of skill path to skill name for all local skills.
        """
        return {skill.path: skill for skill in self.msm.local_skills.values()}

    @property
    def skill_gid(self):
        """Skill identifier recognized by backend and core.

        The skill_gid contains the device ID if the skill has been modified
        on that device.  MSM does not know the ID of the device.  So, if it
        finds a modified skill, it prepends the skill name portion of the ID
        with "@|".

        The device ID is known to this class.  To "finalize" the skill_gid,
        insert the device ID between the "@" and the "|"
        """
        api = self.api or DeviceApi()
        if api.identity.uuid:
            skills = self.get_local_skills()
            skill_dir = str(self.skill_directory)
            if skill_dir not in skills:
                self.msm.clear_cache()
                skills = self.get_local_skills()
            skill = skills[skill_dir]
            # If modified prepend the device uuid
            self._skill_gid = skill.skill_gid.replace(
                '@|',
                '@{}|'.format(api.identity.uuid)
            )

            return self._skill_gid
        else:
            return None

    @property
    def msm_skill_display_name(self):
        """Display name defined in MSM for use in settings meta."""
        if self._msm_skill_display_name is None:
            skills = {
                skill.path: skill for skill in self.msm.local_skills.values()
            }
            skill = skills[str(self.skill_directory)]
            self._msm_skill_display_name = skill.meta_info.get('display_name')

        return self._msm_skill_display_name

    @property
    def settings_meta_path(self):
        """Fully qualified path to the settingsmeta file."""
        if self._settings_meta_path is None:
            if self.yaml_path.is_file():
                self._settings_meta_path = self.yaml_path
            else:
                self._settings_meta_path = self.json_path

        return self._settings_meta_path

    def upload(self):
        """Upload the contents of the settingsmeta file to Mycroft servers.

        The settingsmeta file does not change often, if at all.  Only perform
        the upload if a change in the file is detected.
        """
        if not self.sync_enabled:
            return
        synced = False
        if is_paired():
            self.api = DeviceApi()
            if self.api.identity.uuid:
                settings_meta_file_exists = (
                    self.json_path.is_file() or
                    self.yaml_path.is_file()
                )
                if settings_meta_file_exists:
                    self._load_settings_meta_file()

                self._update_settings_meta()
                LOG.debug('Uploading settings meta for ' + self.skill_gid)
                synced = self._issue_api_call()
            else:
                LOG.debug('settingsmeta.json not uploaded - no identity')
        else:
            LOG.debug('settingsmeta.json not uploaded - device is not paired')

        if not synced and not self._stopped:
            self.upload_timer = Timer(ONE_MINUTE, self.upload)
            self.upload_timer.daemon = True
            self.upload_timer.start()

    def stop(self):
        """Stop upload attempts if Timer is running."""
        if self.upload_timer:
            self.upload_timer.cancel()
        # Set stopped flag if upload is running when stop is called.
        self._stopped = True

    def _load_settings_meta_file(self):
        """Read the contents of the settingsmeta file into memory."""
        _, ext = os.path.splitext(str(self.settings_meta_path))
        is_json_file = self.settings_meta_path.suffix == ".json"
        try:
            with open(str(self.settings_meta_path)) as meta_file:
                if is_json_file:
                    self.settings_meta = json.load(meta_file)
                else:
                    self.settings_meta = yaml.safe_load(meta_file)
        except Exception:
            LOG.error(f"Failed to load settingsmeta file: {self.settings_meta_path}")

    def _update_settings_meta(self):
        """Make sure the skill gid and name are included in settings meta.

        Even if a skill does not have a settingsmeta file, we will upload
        settings meta JSON containing a skill gid and name
        """
        # Insert skill_gid and display_name
        self.settings_meta.update(
            skill_gid=self.skill_gid,
            display_name=(
                self.msm_skill_display_name or
                self.settings_meta.get('name') or
                get_display_name(self.skill_name)
            )
        )
        for deprecated in ('color', 'identifier', 'name'):
            if deprecated in self.settings_meta:
                log_msg = (
                    'DEPRECATION WARNING: The "{}" attribute in the '
                    'settingsmeta file is no longer supported.'
                )
                LOG.warning(log_msg.format(deprecated))
                del(self.settings_meta[deprecated])

    def _issue_api_call(self):
        """Use the API to send the settings meta to the server."""
        try:
            self.api.upload_skill_metadata(self.settings_meta)
        except Exception as e:
            LOG.error(f'Failed to upload skill settings meta for {self.skill_gid}')
            return False
        return True


# Path to remote cache
REMOTE_CACHE = Path(xdg_cache_home, BASE_FOLDER, 'remote_skill_settings.json')


def load_remote_settings_cache():
    """Load cached remote skill settings.

    Returns:
        (dict) Loaded remote settings cache or None of none exists.
    """
    remote_settings = {}
    if REMOTE_CACHE.exists():
        try:
            with open(str(REMOTE_CACHE)) as cache:
                remote_settings = json.load(cache)
        except Exception as error:
            LOG.warning('Failed to read remote_cache ({})'.format(error))
    return remote_settings


def save_remote_settings_cache(remote_settings):
    """Save updated remote settings to cache file.

    Args:
        remote_settings (dict): downloaded remote settings.
    """
    try:
        ensure_directory_exists(dirname(str(REMOTE_CACHE)))
        with open(str(REMOTE_CACHE), 'w') as cache:
            json.dump(remote_settings, cache)
    except Exception as error:
        LOG.warning('Failed to write remote_cache. ({})'.format(error))
    else:
        LOG.debug('Updated local cache of remote skill settings.')


class SkillSettingsDownloader:
    """Manages download of skill settings.

    Performs settings download on a repeating Timer. If a change is seen
    the data is sent to the relevant skill.
    """

    def __init__(self, bus):
        self.bus = bus
        self.continue_downloading = True
        self.last_download_result = load_remote_settings_cache()

        self.api = DeviceApi()
        self.download_timer = None
       
        if is_backend_disabled():
            self.sync_enabled = False
        else:
            self.sync_enabled = Configuration.get()["server"] \
                .get("sync_skill_settings", False)

        if not self.sync_enabled:
            LOG.info("Skill settings sync is disabled, backend settings will "
                     "not be downloaded")

    def stop_downloading(self):
        """Stop synchronizing backend and core."""
        self.continue_downloading = False
        if self.download_timer:
            self.download_timer.cancel()

    # TODO: implement as websocket
    def download(self, message=None):
        """Download the settings stored on the backend and check for changes

        When used as a messagebus handler a message is passed but not used.
        """
        if not self.sync_enabled:
            return
        if is_paired():
            remote_settings = self._get_remote_settings()
            if remote_settings:
                settings_changed = self.last_download_result != remote_settings
                if settings_changed:
                    LOG.debug('Skill settings changed since last download')
                    self._emit_settings_change_events(remote_settings)
                    self.last_download_result = remote_settings
                    save_remote_settings_cache(remote_settings)
                else:
                    LOG.debug('No skill settings changes since last download')
        else:
            LOG.debug('Settings not downloaded - device is not paired')
        # If this method is called outside of the timer loop, ensure the
        # existing timer is canceled before starting a new one.
        if self.download_timer:
            self.download_timer.cancel()

        if self.continue_downloading:
            self.download_timer = Timer(ONE_MINUTE, self.download)
            self.download_timer.daemon = True
            self.download_timer.start()

    def _get_remote_settings(self):
        """Get the settings for this skill from the server

        Returns:
            skill_settings (dict or None): returns a dict on success, else None
        """
        try:
            remote_settings = self.api.get_skill_settings()
        except Exception:
            LOG.error('Failed to download remote settings from server.')
            remote_settings = None

        return remote_settings

    def _emit_settings_change_events(self, remote_settings):
        """Emit changed settings events for each affected skill."""
        for skill_gid, skill_settings in remote_settings.items():
            settings_changed = False
            try:
                previous_settings = self.last_download_result.get(skill_gid)
            except Exception:
                LOG.error('error occurred handling setting change events')
            else:
                if previous_settings != skill_settings:
                    settings_changed = True
            if settings_changed:
                log_msg = 'Emitting skill.settings.change event for skill {} '
                LOG.info(log_msg.format(skill_gid))
                message = Message(
                    'mycroft.skills.settings.changed',
                    data={skill_gid: skill_settings}
                )
                self.bus.emit(message)
