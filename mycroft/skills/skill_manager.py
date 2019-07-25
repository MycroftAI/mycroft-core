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
import os
import time
from glob import glob
from threading import Thread, Event

from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
from .core import MainModule
from .msm_wrapper import create_msm as msm_creator
from .skill_loader import SkillLoader
from .skill_updater import SkillUpdater

SKILL_MAIN_MODULE = MainModule + '.py'


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
        self.skill_loaders = {}
        self.enclosure = EnclosureAPI(bus)
        self.initial_load_complete = False
        self.msm = self.create_msm()
        self.num_install_retries = 0
        self._define_message_bus_events()
        self.skill_updater = SkillUpdater(self.bus)
        self.daemon = True

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
        """Trigger upload of skills manifest after pairing."""
        self.skill_updater.post_manifest()

    def _unload_removed_skills(self):
        """Shutdown removed skills."""
        paths = self._get_skill_directories()
        skills = self.skill_loaders
        # Find loaded skills that doesn't exist on disk
        removed_skills = [str(s) for s in skills.keys() if str(s) not in paths]
        for s in removed_skills:
            LOG.info('removing {}'.format(s))
            try:
                LOG.debug('Removing: {}'.format(skills[s]))
                skills[s]['instance'].default_shutdown()
            except Exception as e:
                LOG.exception(e)
            self.skill_loaders.pop(s)

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
                self._load_skill(skill.path)
            else:
                LOG.error(
                    'Priority skill {} can\'t be found'.format(skill_name)
                )

    def run(self):
        """Load skills and update periodically from disk and internet."""
        self._remove_git_locks()
        self._connected_event.wait()
        self._load_on_startup()

        # Scan the file folder that contains Skills.  If a Skill is updated,
        # unload the existing version from memory and reload from the disk.
        while not self._stop_event.is_set():
            self._reload_modified_skills()
            self._unload_removed_skills()
            self._update_skills()
            time.sleep(2)  # Pause briefly before beginning next scan

    def _remove_git_locks(self):
        """If git gets killed from an abrupt shutdown it leaves lock files."""
        for i in glob(os.path.join(self.msm.skills_dir, '*/.git/index.lock')):
            LOG.warning('Found and removed git lock file: ' + i)
            os.remove(i)

    def _load_on_startup(self):
        """Handle initial skill load."""
        LOG.info('Loading installed skills...')
        while not self.initial_load_complete:
            skill_dirs = self._get_skill_directories()
            if skill_dirs:
                for skill_dir in skill_dirs:
                    self._load_skill(skill_dir)
                if len(self.skill_loaders) == len(skill_dirs):
                    self.initial_load_complete = True
            time.sleep(2)

        LOG.info("Skills all loaded!")
        self.bus.emit(Message('mycroft.skills.initialized'))

    def _reload_modified_skills(self):
        """Handle reload of recently changed skill(s)"""
        LOG.debug('Checking for modified skills')
        for skill_dir in self._get_skill_directories():
            self._load_skill(skill_dir)

    def _load_skill(self, skill_directory):
        try:
            skill_loader = SkillLoader(self.bus, skill_directory)
            skill_loader.load()
            self.skill_loaders[skill_directory] = skill_loader
        except Exception as e:
            LOG.error('Load of skill {} failed!'.format(skill_directory))
            LOG.exception(e)

    def _get_skill_directories(self):
        skill_glob = glob(os.path.join(self.msm.skills_dir, '*/'))

        skill_directories = []
        for skill_dir in skill_glob:
            # TODO: all python packages must have __init__.py!  Better way?
            # check if folder is a skill (must have __init__.py)
            if SKILL_MAIN_MODULE in os.listdir(skill_dir):
                skill_directories.append(skill_dir.rstrip('/'))

        return skill_directories

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
            for s in self.skill_loaders:
                is_active = (self.skill_loaders[s].get('active', True) and
                             self.skill_loaders[s].get('instance') is not None)
                info[os.path.basename(s)] = {
                    'active': is_active,
                    'id': self.skill_loaders[s]['id']
                }
            self.bus.emit(Message('mycroft.skills.list', data=info))
        except Exception as e:
            LOG.exception(e)

    def __deactivate_skill(self, skill):
        """ Deactivate a skill. """
        for s in self.skill_loaders:
            if skill in s:
                skill = s
                break
        try:
            self.skill_loaders[skill]['active'] = False
            self.skill_loaders[skill]['instance'].default_shutdown()
        except Exception as e:
            LOG.error('Couldn\'t deactivate skill, {}'.format(repr(e)))

    def deactivate_skill(self, message):
        """Deactivate a skill."""
        try:
            skill = message.data['skill']
            if skill in [os.path.basename(s) for s in self.skill_loaders]:
                self.__deactivate_skill(skill)
        except Exception as e:
            LOG.error('Couldn\'t deactivate skill, {}'.format(repr(e)))

    def deactivate_except(self, message):
        """Deactivate all skills except the provided."""
        try:
            skill_to_keep = message.data['skill']
            LOG.info('DEACTIVATING ALL SKILLS EXCEPT {}'.format(skill_to_keep))
            loaded_skill_file_names = [
                os.path.basename(i) for i in self.skill_loaders
            ]
            if skill_to_keep in loaded_skill_file_names:
                for skill in self.skill_loaders:
                    if os.path.basename(skill) != skill_to_keep:
                        self.__deactivate_skill(skill)
            else:
                LOG.info('Couldn\'t find skill')
        except Exception as e:
            LOG.error('Error during skill removal, {}'.format(repr(e)))

    def __activate_skill(self, skill):
        if not self.skill_loaders[skill].get('active', True):
            self.skill_loaders[skill]['loaded'] = False
            self.skill_loaders[skill]['active'] = True

    def activate_skill(self, message):
        """Activate a deactivated skill."""
        try:
            skill = message.data['skill']
            if skill == 'all':
                for s in self.skill_loaders:
                    self.__activate_skill(s)
            else:
                for s in self.skill_loaders:
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
        for name, skill_info in self.skill_loaders.items():
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
        for skill in self.skill_loaders:
            if self.skill_loaders[skill]["id"] == skill_id:
                instance = self.skill_loaders[skill].get("instance")
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
