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
"""Periodically run by skill manager to load skills into memory."""
import gc
import importlib
import os
import sys
from inspect import isclass, signature
from os import path, makedirs
from time import time

from ovos_utils.configuration import get_xdg_base, is_using_xdg, get_xdg_data_dirs, get_xdg_data_save_path
from ovos_plugin_manager.skills import find_skill_plugins

from mycroft.configuration import Configuration
from mycroft.messagebus import Message
from mycroft.skills.mycroft_skill.mycroft_skill import MycroftSkill
from mycroft.skills.settings import SettingsMetaUploader
from mycroft.util.log import LOG

SKILL_MAIN_MODULE = '__init__.py'


def _get_skill_folder_name(conf=None):
    # TODO deprecate on version 0.0.3 when the warning is no longer needed
    conf = conf or Configuration.get(remote=False)
    folder = conf["skills"].get("directory")

    if not folder:
        # also check under old "msm" section for backwards compat
        folder = conf["skills"].get("msm", {}).get("directory")
        if folder:
            LOG.warning("msm has been deprecated\n"
                        "please move 'skills.msm.directory' to 'skills.directory' in mycroft.conf\n"
                        "support will be removed on version 0.0.3")
        else:
            folder = "skills"
    return folder


def get_skill_directories(conf=None):
    """ returns list of skill directories ordered by expected loading order

    This corresponds to:
    - XDG_DATA_DIRS
    - default directory (see get_default_skills_directory method for details)
    - user defined extra directories

    Each directory contains individual skill folders to be loaded

    If a skill exists in more than one directory (same folder name) previous instances will be ignored
        ie. directories at the end of the list have priority over earlier directories

    NOTE: empty folders are interpreted as disabled skills

    new directories can be defined in mycroft.conf by specifying a full path
    each extra directory is expected to contain individual skill folders to be loaded

    the xdg folder name can also be changed, it defaults to "skills"
        eg. ~/.local/share/mycroft/FOLDER_NAME

    {
        "skills": {
            "directory": "skills",
            "extra_directories": ["path/to/extra/dir/to/scan/for/skills"]
        }
    }

    Args:
        conf (dict): mycroft.conf dict, will be loaded automatically if None
    """
    # the contents of each skills directory must be individual skill folders
    # we are still dependent on the mycroft-core structure of skill_id/__init__.py

    conf = conf or Configuration.get(remote=False)
    folder = _get_skill_folder_name(conf)

    # load all valid XDG paths
    # NOTE: skills are actually code, but treated as user data!
    # they should be considered applets rather than full applications
    skill_locations = list(reversed(
        [os.path.join(p, folder) for p in get_xdg_data_dirs()]
    ))

    # load the default skills folder
    # only meaningful if xdg support is disabled
    default = get_default_skills_directory(conf)
    if default not in skill_locations:
        skill_locations.append(default)

    # load additional explicitly configured directories
    conf = conf.get("skills") or {}
    # extra_directories is a list of directories containing skill subdirectories
    # NOT a list of individual skill folders
    skill_locations += conf.get("extra_directories") or []
    return skill_locations


def get_default_skills_directory(conf=None):
    """ return default directory to scan for skills

    This is only meaningful if xdg is disabled in ovos.conf
    If xdg is enabled then data_dir is always XDG_DATA_DIR
    If xdg is disabled then data_dir by default corresponds to /opt/mycroft

    users can define the data directory in mycroft.conf
    the skills folder name (relative to data_dir) can also be defined there

    NOTE: folder name also impacts all XDG skill directories!

    {
        "data_dir": "/opt/mycroft",
        "skills": {
            "directory": "skills"
        }
    }

    Args:
        conf (dict): mycroft.conf dict, will be loaded automatically if None
    """
    conf = conf or Configuration.get(remote=False)
    path_override = conf["skills"].get("directory_override")
    folder = _get_skill_folder_name()

    # if .conf wants to use a specific path, use it!
    if path_override:
        LOG.warning("'directory_override' is deprecated!\n"
                    "It will no longer be supported after version 0.0.3\n"
                    "add the new path to 'extra_directories' instead")
        skills_folder = path_override
    # if xdg is disabled, ignore it!
    elif not is_using_xdg():
        # old style mycroft-core skills path definition
        data_dir = conf.get("data_dir") or "/opt/" + get_xdg_base()
        skills_folder = path.join(data_dir, folder)
    else:
        skills_folder = os.path.join(get_xdg_data_save_path(), folder)
    # create folder if needed
    try:
        makedirs(skills_folder, exist_ok=True)
    except PermissionError:  # old style /opt/mycroft/skills not available
        skills_folder = os.path.join(get_xdg_data_save_path(), folder)
        makedirs(skills_folder, exist_ok=True)

    return path.expanduser(skills_folder)


def remove_submodule_refs(module_name):
    """Ensure submodules are reloaded by removing the refs from sys.modules.

    Python import system puts a reference for each module in the sys.modules
    dictionary to bypass loading if a module is already in memory. To make
    sure skills are completely reloaded these references are deleted.

    Args:
        module_name: name of skill module.
    """
    submodules = []
    LOG.debug(f'Skill module: {module_name}')
    # Collect found submodules
    for m in sys.modules:
        if m.startswith(module_name + '.'):
            submodules.append(m)
    # Remove all references them to in sys.modules
    for m in submodules:
        LOG.debug(f'Removing sys.modules ref for {m}')
        del sys.modules[m]


def load_skill_module(path, skill_id):
    """Load a skill module

    This function handles the differences between python 3.4 and 3.5+ as well
    as makes sure the module is inserted into the sys.modules dict.

    Args:
        path: Path to the skill main file (__init__.py)
        skill_id: skill_id used as skill identifier in the module list
    """
    module_name = skill_id.replace('.', '_')

    remove_submodule_refs(module_name)

    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _bad_mod_times(mod_times):
    """Return all entries with modification time in the future.

    Args:
        mod_times (dict): dict mapping file paths to modification times.

    Returns:
        List of files with bad modification times.
    """
    current_time = time()
    return [path for path in mod_times if mod_times[path] > current_time]


def _get_last_modified_time(path):
    """Get the last modified date of the most recently updated file in a path.

    Exclude compiled python files, hidden directories and the settings.json
    file.

    Args:
        path: skill directory to check

    Returns:
        int: time of last change
    """
    all_files = []
    for root_dir, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            ignore_file = (
                    f.endswith('.pyc') or
                    f == 'settings.json' or
                    f.startswith('.') or
                    f.endswith('.qmlc')
            )
            if not ignore_file:
                all_files.append(os.path.join(root_dir, f))

    # check files of interest in the skill root directory
    mod_times = {f: os.path.getmtime(f) for f in all_files}
    # Ensure modification times are valid
    bad_times = _bad_mod_times(mod_times)
    if bad_times:
        raise OSError(f'{bad_times} had bad modification times')
    if all_files:
        return max(os.path.getmtime(f) for f in all_files)
    else:
        return 0


def get_skill_class(skill_module):
    """Find MycroftSkill based class in skill module.

    Arguments:
        skill_module (module): module to search for Skill class

    Returns:
        (MycroftSkill): Found subclass of MycroftSkill or None.
    """
    if callable(skill_module):
        # it's a skill plugin
        # either a func that returns the skill or the skill class itself
        return skill_module

    candidates = []
    for name, obj in skill_module.__dict__.items():
        if isclass(obj):
            if issubclass(obj, MycroftSkill) and obj is not MycroftSkill:
                candidates.append(obj)

    for candidate in list(candidates):
        others = [clazz for clazz in candidates if clazz != candidate]
        # if we found a subclass of this candidate, it is not the final skill
        if any(issubclass(clazz, candidate) for clazz in others):
            candidates.remove(candidate)

    if candidates:
        if len(candidates) > 1:
            LOG.warning(f"Multiple skills found in a single file!\n"
                        f"{candidates}")
        LOG.debug(f"Loading skill class: {candidates[0]}")
        return candidates[0]
    return None


def get_create_skill_function(skill_module):
    """Find create_skill function in skill module.

    Arguments:
        skill_module (module): module to search for create_skill function

    Returns:
        (function): Found create_skill function or None.
    """
    if hasattr(skill_module, "create_skill") and \
            callable(skill_module.create_skill):
        return skill_module.create_skill
    return None


class SkillLoader:
    def __init__(self, bus, skill_directory):
        self.bus = bus
        self.skill_directory = skill_directory
        self.skill_id = os.path.basename(skill_directory)
        self.load_attempted = False
        self.loaded = False
        self.last_modified = 0
        self.last_loaded = 0
        self.instance = None
        self.active = True
        self.config = Configuration.get()

        self.modtime_error_log_written = False

    @property
    def is_blacklisted(self):
        """Boolean value representing whether or not a skill is blacklisted."""
        blacklist = self.config['skills'].get('blacklisted_skills', [])
        if self.skill_id in blacklist:
            return True
        else:
            return False

    def reload_needed(self):
        """Load an unloaded skill or reload unloaded/changed skill.

        Returns:
             bool: if the skill was loaded/reloaded
        """
        # TODO on ntp sync last_modified needs to be updated
        try:
            self.last_modified = _get_last_modified_time(self.skill_directory)
        except OSError as err:
            self.last_modified = self.last_loaded
            if not self.modtime_error_log_written:
                self.modtime_error_log_written = True
                LOG.error(f'Failed to get last_modification time ({err})')
        else:
            self.modtime_error_log_written = False

        modified = self.last_modified > self.last_loaded

        reload_allowed = (
                self.active and
                (self.instance is None or self.instance.reload_skill)
        )
        return modified and reload_allowed

    def reload(self):
        LOG.info('ATTEMPTING TO RELOAD SKILL: ' + self.skill_id)
        if self.instance:
            if not self.instance.reload_skill:
                LOG.info("skill does not allow reloading!")
                return False  # not allowed
            self._unload()
        return self._load()

    def load(self):
        LOG.info('ATTEMPTING TO LOAD SKILL: ' + self.skill_id)
        return self._load()

    def _unload(self):
        """Remove listeners and stop threads before loading"""
        self._execute_instance_shutdown()
        if self.config.get("debug", False):
            self._garbage_collect()
        self.loaded = False
        self._emit_skill_shutdown_event()

    def unload(self):
        if self.instance:
            self._execute_instance_shutdown()
        self.loaded = False

    def activate(self):
        self.active = True
        self.load()

    def deactivate(self):
        self.active = False
        self.unload()

    def _execute_instance_shutdown(self):
        """Call the shutdown method of the skill being reloaded."""
        try:
            self.instance.default_shutdown()
        except Exception:
            LOG.exception(f'An error occurred while shutting down {self.skill_id}')
        else:
            LOG.info(f'Skill {self.skill_id} shut down successfully')

    def _garbage_collect(self):
        """Invoke Python garbage collector to remove false references"""
        gc.collect()
        # Remove two local references that are known
        refs = sys.getrefcount(self.instance) - 2
        if refs > 0:
            LOG.warning(
                f"After shutdown of {self.skill_id} there are still {refs} references "
                "remaining. The skill won't be cleaned from memory."
            )

    def _emit_skill_shutdown_event(self):
        message = Message("mycroft.skills.shutdown",
                          {"path": self.skill_directory, "id": self.skill_id})
        self.bus.emit(message)

    def _load(self):
        self._prepare_for_load()
        if self.is_blacklisted:
            self._skip_load()
        else:
            skill_module = self._load_skill_source()
            if skill_module and self._create_skill_instance(skill_module):
                self.loaded = True

        self.last_loaded = time()
        self._communicate_load_status()
        if self.loaded:
            self._prepare_settings_meta()
        return self.loaded

    def _prepare_settings_meta(self):
        settings_meta = SettingsMetaUploader(self.skill_directory,
                                             self.instance.skill_id)
        self.instance.settings_meta = settings_meta

    def _prepare_for_load(self):
        self.load_attempted = True
        self.loaded = False
        self.instance = None

    def _skip_load(self):
        LOG.info(f'Skill {self.skill_id} is blacklisted - it will not be loaded')

    def _load_skill_source(self):
        """Use Python's import library to load a skill's source code."""
        main_file_path = os.path.join(self.skill_directory, SKILL_MAIN_MODULE)
        skill_module = None
        if not os.path.exists(main_file_path):
            LOG.error(f'Failed to load {self.skill_id} due to a missing file.')
        else:
            try:
                skill_module = load_skill_module(main_file_path, self.skill_id)
            except Exception as e:
                LOG.exception(f'Failed to load skill: {self.skill_id} ({e})')
        return skill_module

    def _create_skill_instance(self, skill_module):
        """create the skill object.

        Arguments:
            skill_module (module): Module to load from

        Returns:
            (bool): True if skill was loaded successfully.
        """
        try:
            skill_creator = get_create_skill_function(skill_module) or \
                            get_skill_class(skill_module)

            # create the skill
            self.instance = skill_creator()

            if not self.instance.is_fully_initialized:
                # finish initialization of skill class
                self.instance._startup(self.bus, self.skill_id)
        except Exception as e:
            LOG.exception(f'Skill __init__ failed with {e}')
            self.instance = None

        return self.instance is not None

    def _communicate_load_status(self):
        if self.loaded:
            message = Message('mycroft.skills.loaded',
                              {"path": self.skill_directory,
                               "id": self.skill_id,
                               "name": self.instance.name,
                               "modified": self.last_modified})
            self.bus.emit(message)
            LOG.info(f'Skill {self.skill_id} loaded successfully')
        else:
            message = Message('mycroft.skills.loading_failure',
                              {"path": self.skill_directory, "id": self.skill_id})
            self.bus.emit(message)
            LOG.error(f'Skill {self.skill_id} failed to load')


class PluginSkillLoader(SkillLoader):
    def __init__(self, bus, skill_id):
        super().__init__(bus, skill_id)
        self.skill_directory = skill_id
        self.skill_id = skill_id

    def reload_needed(self):
        return False

    def _create_skill_instance(self, skill_module):
        if super()._create_skill_instance(skill_module):
            self.skill_directory = self.instance.root_dir
            return True
        return False

    def load(self, skill_module):
        LOG.info('ATTEMPTING TO LOAD PLUGIN SKILL: ' + self.skill_id)
        self._prepare_for_load()
        if self.is_blacklisted:
            self._skip_load()
        else:
            self.loaded = self._create_skill_instance(skill_module)

        self.last_loaded = time()
        self._communicate_load_status()
        if self.loaded:
            self._prepare_settings_meta()
        return self.loaded
