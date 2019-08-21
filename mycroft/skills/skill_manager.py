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
from glob import glob
from threading import Thread, Event
from time import sleep, time

from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
from .msm_wrapper import create_msm as msm_creator, build_msm_config
from .skill_loader import SkillLoader
from .skill_updater import SkillUpdater

SKILL_MAIN_MODULE = '__init__.py'


class SkillManager(Thread):
    _msm = None

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
        self.num_install_retries = 0
        self._define_message_bus_events()
        self.skill_updater = SkillUpdater()
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

    @property
    def msm(self):
        if self._msm is None:
            msm_config = build_msm_config(self.config)
            self._msm = msm_creator(msm_config)

        return self._msm

    @staticmethod
    def create_msm():
        LOG.debug('instantiating msm via static method...')
        msm_config = build_msm_config(Configuration.get())
        msm_instance = msm_creator(msm_config)

        return msm_instance

    def schedule_now(self, _):
        self.skill_updater.next_download = time() - 1

    def handle_paired(self, _):
        """Trigger upload of skills manifest after pairing."""
        self.skill_updater.post_manifest()

    def load_priority(self):
        skills = {skill.name: skill for skill in self.msm.all_skills}
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
            self._load_new_skills()
            self._unload_removed_skills()
            self._update_skills()
            sleep(2)  # Pause briefly before beginning next scan

    def _remove_git_locks(self):
        """If git gets killed from an abrupt shutdown it leaves lock files."""
        for i in glob(os.path.join(self.msm.skills_dir, '*/.git/index.lock')):
            LOG.warning('Found and removed git lock file: ' + i)
            os.remove(i)

    def _load_on_startup(self):
        """Handle initial skill load."""
        LOG.info('Loading installed skills...')
        self._load_new_skills()
        LOG.info("Skills all loaded!")
        self.bus.emit(Message('mycroft.skills.initialized'))

    def _reload_modified_skills(self):
        """Handle reload of recently changed skill(s)"""
        for skill_dir in self._get_skill_directories():
            skill_loader = self.skill_loaders.get(skill_dir)
            if skill_loader is not None and skill_loader.reload_needed():
                skill_loader.reload()

    def _load_new_skills(self):
        """Handle load of skills installed since startup."""
        for skill_dir in self._get_skill_directories():
            if skill_dir not in self.skill_loaders:
                self._load_skill(skill_dir)

    def _load_skill(self, skill_directory):
        try:
            skill_loader = SkillLoader(self.bus, skill_directory)
            skill_loader.load()
        except Exception:
            LOG.exception('Load of skill {} failed!'.format(skill_directory))
        finally:
            self.skill_loaders[skill_directory] = skill_loader

    def _get_skill_directories(self):
        skill_glob = glob(os.path.join(self.msm.skills_dir, '*/'))

        skill_directories = []
        for skill_dir in skill_glob:
            # TODO: all python packages must have __init__.py!  Better way?
            # check if folder is a skill (must have __init__.py)
            if SKILL_MAIN_MODULE in os.listdir(skill_dir):
                skill_directories.append(skill_dir.rstrip('/'))
            else:
                LOG.debug('Found skills directory with no skill: ' + skill_dir)

        return skill_directories

    def _unload_removed_skills(self):
        """Shutdown removed skills."""
        skill_dirs = self._get_skill_directories()
        # Find loaded skills that don't exist on disk
        removed_skills = [
            s for s in self.skill_loaders.keys() if s not in skill_dirs
        ]
        for skill_dir in removed_skills:
            skill = self.skill_loaders[skill_dir]
            LOG.info('removing {}'.format(skill.skill_id))
            try:
                skill.unload()
            except Exception:
                LOG.exception('Failed to shutdown skill ' + skill.id)
            del self.skill_loaders[skill_dir]

    def _update_skills(self):
        """Update skills once an hour if update is enabled"""
        do_skill_update = (
            time() >= self.skill_updater.next_download and
            self.skills_config["auto_update"]
        )
        if do_skill_update:
            self.skill_updater.update_skills()

    def send_skill_list(self, _):
        """Send list of loaded skills."""
        try:
            message_data = {}
            for skill_dir, skill_loader in self.skill_loaders.items():
                message_data[skill_loader.skill_id] = dict(
                    active=skill_loader.active and skill_loader.loaded,
                    id=skill_loader.skill_id
                )
            self.bus.emit(Message('mycroft.skills.list', data=message_data))
        except Exception:
            LOG.exception('Failed to send skill list')

    def deactivate_skill(self, message):
        """Deactivate a skill."""
        try:
            for skill_loader in self.skill_loaders.values():
                if message.data['skill'] == skill_loader.skill_id:
                    skill_loader.deactivate()
        except Exception:
            LOG.exception('Failed to deactivate ' + message.data['skill'])

    def deactivate_except(self, message):
        """Deactivate all skills except the provided."""
        try:
            skill_to_keep = message.data['skill']
            LOG.info('Deactivating all skills except {}'.format(skill_to_keep))
            loaded_skill_file_names = [
                os.path.basename(skill_dir) for skill_dir in self.skill_loaders
            ]
            if skill_to_keep in loaded_skill_file_names:
                for skill in self.skill_loaders.values():
                    if skill.skill_id != skill_to_keep:
                        skill.deactivate()
            else:
                LOG.info('Couldn\'t find skill ' + message.data['skill'])
        except Exception:
            LOG.exception('An error occurred during skill deactivation!')

    def activate_skill(self, message):
        """Activate a deactivated skill."""
        try:
            for skill_loader in self.skill_loaders.values():
                if (message.data['skill'] in ('all', skill_loader.skill_id) and
                        not skill_loader.active):
                    skill_loader.activate()
        except Exception:
            LOG.exception('Couldn\'t activate skill')

    def stop(self):
        """Tell the manager to shutdown."""
        self._stop_event.set()

        # Do a clean shutdown of all skills
        for skill_loader in self.skill_loaders.values():
            if skill_loader.instance is not None:
                try:
                    skill_loader.instance.default_shutdown()
                except Exception:
                    LOG.exception(
                        'Failed to shut down skill: ' + skill_loader.skill_id
                    )

    def handle_converse_request(self, message):
        """Check if the targeted skill id can handle conversation

        If supported, the conversation is invoked.
        """
        skill_id = message.data['skill_id']

        # loop trough skills list and call converse for skill with skill_id
        skill_found = False
        for skill_loader in self.skill_loaders.values():
            if skill_loader.skill_id == skill_id:
                skill_found = True
                if not skill_loader.loaded:
                    error_message = 'converse requested but skill not loaded'
                    self._emit_converse_error(message, skill_id, error_message)
                    break
                try:
                    self._emit_converse_response(message, skill_loader)
                except BaseException as e:
                    error_message = 'exception in converse method'
                    LOG.exception(error_message)
                    self._emit_converse_error(message, skill_id, error_message)
                finally:
                    break

        if not skill_found:
            error_message = 'skill id does not exist'
            self._emit_converse_error(message, skill_id, error_message)

    def _emit_converse_error(self, message, skill_id, error_msg):
        reply = message.reply(
            'skill.converse.error',
            data=dict(skill_id=skill_id, error=error_msg)
        )
        self.bus.emit(reply)

    def _emit_converse_response(self, message, skill_loader):
        utterances = message.data['utterances']
        lang = message.data['lang']
        result = skill_loader.instance.converse(utterances, lang)
        reply = message.reply(
            'skill.converse.response',
            data=dict(skill_id=skill_loader.skill_id, result=result)
        )
        self.bus.emit(reply)
