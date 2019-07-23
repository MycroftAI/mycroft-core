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
"""Load, update and manage skills on this device."""
import gc
import os
import sys
import time
from glob import glob
from threading import Thread, Event

from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
from .core import load_skill, create_skill_descriptor, MainModule
from .msm_wrapper import create_msm as msm_creator
from .skill_updater import SkillUpdater


def _get_last_modified_date(path):
    """Get the last modified date of the most recently updated file in a path.

    Exclude compiled python files, hidden directories and the settings.json
    file.

    Arguments:
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
    return max(os.path.getmtime(f) for f in all_files)


class SkillManager(Thread):
    def __init__(self, bus):
        """Constructor

        Arguments:
            bus (event emitter): Mycroft messagebus connection
        """
        super(SkillManager, self).__init__()
        self.bus = bus
        self._stop_event = Event()
        self._connected_event = Event()
        self.loaded_skills = {}
        self.enclosure = EnclosureAPI(bus)

        # Schedule install/update of default skill
        self.msm = self.create_msm()
        self.num_install_retries = 0

        self._define_message_bus_events()
        self.skill_updater = SkillUpdater(self.bus)

    def _define_message_bus_events(self):
        """Define message bus events with handlers defined in this class."""
        # Conversation management
        self.bus.on('skill.converse.request', self.handle_converse_request)

        # Update on initial connection
        self.bus.on(
            'mycroft.internet.connected',
            lambda x: self._connected_event.set()
        )

        # Update upon request
        self.bus.on('skillmanager.update', self.schedule_now)
        self.bus.on('skillmanager.list', self.send_skill_list)
        self.bus.on('skillmanager.deactivate', self.deactivate_skill)
        self.bus.on('skillmanager.keep', self.deactivate_except)
        self.bus.on('skillmanager.activate', self.activate_skill)
        self.bus.on('mycroft.paired', self.handle_paired)

    @property
    def config(self):
        return Configuration.get()

    @property
    def skills_config(self):
        return Configuration.get()['skills']

    @staticmethod
    def create_msm():
        return msm_creator(Configuration.get())

    def schedule_now(self, _):
        self.skill_updater.next_download = time.time() - 1

    def handle_paired(self, _):
        """ Trigger upload of skills manifest after pairing. """
        self.skill_updater.post_manifest()

    def _unload_removed(self, paths):
        """ Shutdown removed skills.

            Arguments:
                paths: list of current directories in the skills folder
        """
        paths = [p.rstrip('/') for p in paths]
        skills = self.loaded_skills
        # Find loaded skills that doesn't exist on disk
        removed_skills = [str(s) for s in skills.keys() if str(s) not in paths]
        for s in removed_skills:
            LOG.info('removing {}'.format(s))
            try:
                LOG.debug('Removing: {}'.format(skills[s]))
                skills[s]['instance'].default_shutdown()
            except Exception as e:
                LOG.exception(e)
            self.loaded_skills.pop(s)

    def _load_or_reload_skill(self, skill_path):
        """Reload unloaded/changed needs if necessary.

        Returns:
             bool: if the skill was loaded/reloaded
        """
        skill_path = skill_path.rstrip('/')
        skill = self.loaded_skills.setdefault(skill_path, {})
        skill.update({"id": os.path.basename(skill_path), "path": skill_path})

        # check if folder is a skill (must have __init__.py)
        if not MainModule + ".py" in os.listdir(skill_path):
            return False

        # getting the newest modified date of skill
        modified = _get_last_modified_date(skill_path)
        last_mod = skill.get("last_modified", 0)

        # checking if skill is loaded and hasn't been modified on disk
        if skill.get("loaded") and modified <= last_mod:
            return False  # Nothing to do!

        # check if skill was modified
        elif skill.get("instance") and modified > last_mod:
            # check if skill has been blocked from reloading
            if (not skill["instance"].reload_skill or
                    not skill.get('active', True)):
                return False

            LOG.debug("Reloading Skill: " + os.path.basename(skill_path))
            # removing listeners and stopping threads
            try:
                skill["instance"].default_shutdown()
            except Exception:
                LOG.exception("An error occured while shutting down {}"
                              .format(skill["instance"].name))

            debug = self.config.get("debug", False)
            if debug:
                gc.collect()  # Collect garbage to remove false references
                # Remove two local references that are known
                refs = sys.getrefcount(skill["instance"]) - 2
                if refs > 0:
                    msg = ("After shutdown of {} there are still "
                           "{} references remaining. The skill "
                           "won't be cleaned from memory.")
                    LOG.warning(msg.format(skill['instance'].name, refs))
            del skill["instance"]
            self.bus.emit(Message("mycroft.skills.shutdown",
                                  {"path": skill_path,
                                   "id": skill["id"]}))

        skill["loaded"] = True
        desc = create_skill_descriptor(skill_path)
        blacklisted_skills = self.skills_config.get("blacklisted_skills", [])
        skill["instance"] = load_skill(desc,
                                       self.bus, skill["id"],
                                       blacklisted_skills)

        skill["last_modified"] = modified
        if skill['instance'] is not None:
            self.bus.emit(Message('mycroft.skills.loaded',
                                  {'path': skill_path,
                                   'id': skill['id'],
                                   'name': skill['instance'].name,
                                   'modified': modified}))
            return True
        else:
            self.bus.emit(Message('mycroft.skills.loading_failure',
                                  {'path': skill_path,
                                   'id': skill['id']}))
        return False

    def load_priority(self):
        skills = {skill.name: skill for skill in self.msm.list()}
        priority_skills = self.skills_config.get("priority_skills", [])
        for skill_name in priority_skills:
            skill = skills.get(skill_name)
            if skill is not None:
                if not skill.is_local:
                    try:
                        skill.install()
                    except Exception:
                        log_msg = 'Downloading priority skill: {} failed'
                        LOG.exception(log_msg.format(skill_name))
                        continue
                self._load_or_reload_skill(skill.path)
            else:
                LOG.error(
                    'Priority skill {} can\'t be found'.format(skill_name)
                )

    def run(self):
        """Load skills and update periodically from disk and internet."""
        self._remove_git_locks()
        self._connected_event.wait()
        has_loaded = False

        # Scan the file folder that contains Skills.  If a Skill is updated,
        # unload the existing version from memory and reload from the disk.
        while not self._stop_event.is_set():
            # Look for recently changed skill(s) needing a reload
            # checking skills dir and getting all skills there
            skill_paths = glob(os.path.join(self.msm.skills_dir, '*/'))
            still_loading = False
            for skill_path in skill_paths:
                try:
                    still_loading = (
                            self._load_or_reload_skill(skill_path) or
                            still_loading
                    )
                except Exception as e:
                    LOG.error('(Re)loading of {} failed ({})'.format(
                        skill_path, repr(e)))
            if not has_loaded and not still_loading and len(skill_paths) > 0:
                has_loaded = True
                LOG.info("Skills all loaded!")
                self.bus.emit(Message('mycroft.skills.initialized'))

            self._unload_removed(skill_paths)
            time.sleep(2)  # Pause briefly before beginning next scan
            self._update_skills()

    def _remove_git_locks(self):
        """If git gets killed from an abrupt shutdown it leaves lock files."""
        for i in glob(os.path.join(self.msm.skills_dir, '*/.git/index.lock')):
            LOG.warning('Found and removed git lock file: ' + i)
            os.remove(i)

    def _update_skills(self):
        """Update skills once an hour if update is enabled"""
        do_skill_update = (
            time.time() >= self.skill_updater.next_download and
            self.skills_config["auto_update"]
        )
        if do_skill_update:
            self.skill_updater.update_skills()

    def send_skill_list(self, _):
        """Send list of loaded skills."""
        try:
            info = {}
            for s in self.loaded_skills:
                is_active = (self.loaded_skills[s].get('active', True) and
                             self.loaded_skills[s].get('instance') is not None)
                info[os.path.basename(s)] = {
                    'active': is_active,
                    'id': self.loaded_skills[s]['id']
                }
            self.bus.emit(Message('mycroft.skills.list', data=info))
        except Exception as e:
            LOG.exception(e)

    def __deactivate_skill(self, skill):
        """ Deactivate a skill. """
        for s in self.loaded_skills:
            if skill in s:
                skill = s
                break
        try:
            self.loaded_skills[skill]['active'] = False
            self.loaded_skills[skill]['instance'].default_shutdown()
        except Exception as e:
            LOG.error('Couldn\'t deactivate skill, {}'.format(repr(e)))

    def deactivate_skill(self, message):
        """Deactivate a skill."""
        try:
            skill = message.data['skill']
            if skill in [os.path.basename(s) for s in self.loaded_skills]:
                self.__deactivate_skill(skill)
        except Exception as e:
            LOG.error('Couldn\'t deactivate skill, {}'.format(repr(e)))

    def deactivate_except(self, message):
        """Deactivate all skills except the provided."""
        try:
            skill_to_keep = message.data['skill']
            LOG.info('DEACTIVATING ALL SKILLS EXCEPT {}'.format(skill_to_keep))
            loaded_skill_file_names = [
                os.path.basename(i) for i in self.loaded_skills
            ]
            if skill_to_keep in loaded_skill_file_names:
                for skill in self.loaded_skills:
                    if os.path.basename(skill) != skill_to_keep:
                        self.__deactivate_skill(skill)
            else:
                LOG.info('Couldn\'t find skill')
        except Exception as e:
            LOG.error('Error during skill removal, {}'.format(repr(e)))

    def __activate_skill(self, skill):
        if not self.loaded_skills[skill].get('active', True):
            self.loaded_skills[skill]['loaded'] = False
            self.loaded_skills[skill]['active'] = True

    def activate_skill(self, message):
        """Activate a deactivated skill."""
        try:
            skill = message.data['skill']
            if skill == 'all':
                for s in self.loaded_skills:
                    self.__activate_skill(s)
            else:
                for s in self.loaded_skills:
                    if skill in s:
                        skill = s
                        break
                self.__activate_skill(skill)
        except Exception as e:
            LOG.error('Couldn\'t activate skill, {}'.format(repr(e)))

    def stop(self):
        """Tell the manager to shutdown."""
        self._stop_event.set()

        # Do a clean shutdown of all skills
        for name, skill_info in self.loaded_skills.items():
            instance = skill_info.get('instance')
            if instance:
                try:
                    instance.default_shutdown()
                except Exception:
                    LOG.exception('Shutting down skill: ' + name)

    def handle_converse_request(self, message):
        """Check if the targeted skill id can handle conversation

        If supported, the conversation is invoked.
        """

        skill_id = message.data["skill_id"]
        utterances = message.data["utterances"]
        lang = message.data["lang"]

        # loop trough skills list and call converse for skill with skill_id
        for skill in self.loaded_skills:
            if self.loaded_skills[skill]["id"] == skill_id:
                instance = self.loaded_skills[skill].get("instance")
                if instance is None:
                    self.bus.emit(message.reply("skill.converse.error",
                                                {"skill_id": skill_id,
                                                 "error": "converse requested"
                                                          " but skill not "
                                                          "loaded"}))
                    return
                try:
                    result = instance.converse(utterances, lang)
                    self.bus.emit(message.reply("skill.converse.response", {
                        "skill_id": skill_id, "result": result}))
                    return
                except BaseException:
                    self.bus.emit(message.reply("skill.converse.error",
                                                {"skill_id": skill_id,
                                                 "error": "exception in "
                                                          "converse method"}))
                    return

        self.bus.emit(message.reply("skill.converse.error",
                                    {"skill_id": skill_id,
                                     "error": "skill id does not exist"}))
