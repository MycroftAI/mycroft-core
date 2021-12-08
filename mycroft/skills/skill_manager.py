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
from threading import Thread, Event, Lock
from time import sleep, time, monotonic
from inspect import signature

from mycroft.api import is_paired
from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from ovos_utils.configuration import get_xdg_base
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
from mycroft.util import connected
from mycroft.skills.msm_wrapper import create_msm as msm_creator, \
    build_msm_config, get_skills_directory
from mycroft.skills.settings import SkillSettingsDownloader
from mycroft.skills.skill_loader import SkillLoader
from mycroft.skills.skill_updater import SkillUpdater
from mycroft.messagebus import MessageBusClient
import xdg.BaseDirectory

SKILL_MAIN_MODULE = '__init__.py'


class UploadQueue:
    """Queue for holding loaders with data that still needs to be uploaded.

    This queue can be used during startup to capture all loaders
    and then processing can be triggered at a later stage when the system is
    connected to the backend.

    After all queued settingsmeta has been processed and the queue is empty
    the queue will set the self.started flag.
    """

    def __init__(self):
        self._queue = []
        self.started = False
        self.lock = Lock()

    def start(self):
        """Start processing of the queue."""
        self.started = True
        self.send()

    def stop(self):
        """Stop the queue, and hinder any further transmissions."""
        self.started = False

    def send(self):
        """Loop through all stored loaders triggering settingsmeta upload."""
        with self.lock:
            queue = self._queue
            self._queue = []
        if queue:
            LOG.info('New Settings meta to upload.')
            for loader in queue:
                if self.started:
                    loader.instance.settings_meta.upload()
                else:
                    break

    def __len__(self):
        return len(self._queue)

    def put(self, loader):
        """Append a skill loader to the queue.

        If a loader is already present it's removed in favor of the new entry.
        """
        if self.started:
            LOG.info('Updating settings meta during runtime...')
        with self.lock:
            # Remove existing loader
            self._queue = [e for e in self._queue if e != loader]
            self._queue.append(loader)


def _shutdown_skill(instance):
    """Shutdown a skill.

    Call the default_shutdown method of the skill, will produce a warning if
    the shutdown process takes longer than 1 second.

    Args:
        instance (MycroftSkill): Skill instance to shutdown
    """
    try:
        ref_time = monotonic()
        # Perform the shutdown
        instance.default_shutdown()

        shutdown_time = monotonic() - ref_time
        if shutdown_time > 1:
            LOG.warning('{} shutdown took {} seconds'.format(instance.skill_id,
                                                             shutdown_time))
    except Exception:
        LOG.exception('Failed to shut down skill: '
                      '{}'.format(instance.skill_id))


def _get_skill_locations(conf=None):
    # the contents of each skills directory must be individual skill folders
    # we are still dependent on the mycroft-core structure of skill_id/__init__.py

    conf = conf or Configuration.get(remote=False)
    # load all valid XDG paths
    # NOTE: skills are actually code, but treated as user data!
    # they should be considered applets rather than full applications
    skill_locations = list(reversed(
        [os.path.join(p, "skills")
         for p in xdg.BaseDirectory.load_data_paths(get_xdg_base())]
    ))

    # load the old hardcoded /opt/mycroft/skills folder
    # needed for integration with msm, assume external tools will install skills here!
    default = get_skills_directory(conf)
    if default not in skill_locations:
        skill_locations.append(default)

    # load additional explicitly configured directories
    conf = conf.get("skills") or {}
    # extra_directories is a list of directories containing skill subdirectories
    # NOT a list of individual skill folders
    skill_locations += conf.get("extra_directories") or []
    return skill_locations


class SkillManager(Thread):
    _msm = None

    def __init__(self, bus, watchdog=None):
        """Constructor

        Args:
            bus (event emitter): Mycroft messagebus connection
            watchdog (callable): optional watchdog function
        """
        super(SkillManager, self).__init__()
        self.bus = bus
        # Set watchdog to argument or function returning None
        self._watchdog = watchdog or (lambda: None)
        self._stop_event = Event()
        self._connected_event = Event()
        self.config = Configuration.get()
        self.upload_queue = UploadQueue()

        self.skill_loaders = {}
        self.enclosure = EnclosureAPI(bus)
        self.initial_load_complete = False
        self.num_install_retries = 0
        self.settings_downloader = SkillSettingsDownloader(self.bus)

        self.empty_skill_dirs = set()  # Save a record of empty skill dirs.

        # Statuses
        self._alive_status = False  # True after priority skills has loaded
        self._loaded_status = False  # True after all skills has loaded

        self.skill_updater = SkillUpdater()
        self._define_message_bus_events()
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
        self.bus.on(
            'mycroft.skills.settings.update',
            self.settings_downloader.download
        )
        self.bus.on('mycroft.skills.trained',
                    self.handle_check_device_readiness)

    def is_device_ready(self):
        is_ready = False
        # different setups will have different needs
        # eg, a server does not care about audio
        # pairing -> device is paired
        # internet -> device is connected to the internet - NOT IMPLEMENTED
        # skills -> skills reported ready
        # speech -> stt reported ready
        # audio -> audio playback reported ready
        # gui -> gui websocket reported ready - NOT IMPLEMENTED
        # enclosure -> enclosure/HAL reported ready - NOT IMPLEMENTED
        services = {k: False for k in
                    self.config.get("ready_settings", ["skills"])}
        start = monotonic()
        while not is_ready:
            is_ready = self.check_services_ready(services)
            if is_ready:
                break
            elif monotonic() - start >= 60:
                raise Exception(
                    f'Timeout waiting for services start. services={services}')
            else:
                sleep(3)
        return is_ready

    def handle_check_device_readiness(self, message):
        if self.is_device_ready():
            LOG.info("Mycroft is all loaded and ready to roll!")
            self.bus.emit(message.reply('mycroft.ready'))

    def check_services_ready(self, services):
        """Report if all specified services are ready.

        services (iterable): service names to check.
        """
        for ser in services:
            services[ser] = False
            if ser == "pairing":
                services[ser] = is_paired()
                continue
            elif ser in ["gui", "enclosure"]:
                # not implemented
                services[ser] = True
                continue
            response = self.bus.wait_for_response(Message(
                'mycroft.{}.is_ready'.format(ser)))
            if response and response.data['status']:
                services[ser] = True
        return all([services[ser] for ser in services])

    @property
    def skills_config(self):
        return self.config['skills']

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

    def _start_settings_update(self):
        LOG.info('Start settings update')
        self.skill_updater.post_manifest(reload_skills_manifest=True)
        self.upload_queue.start()
        LOG.info('All settings meta has been processed or upload has started')
        self.settings_downloader.download()
        LOG.info('Skill settings downloading has started')

    def handle_paired(self, _):
        """Trigger upload of skills manifest after pairing."""
        self._start_settings_update()

    def load_priority(self):
        # NOTE: mycroft uses the skill name, this is not deterministic! msm
        # decides what the name is based on the meta info from selene,
        # if missing it uses folder name (skill_id), for backwards compat
        # name is still support but skill_id is recommended! the name can be
        # changed at any time and mess up the .conf, if the skill_id changes
        # lots of other stuff will break so you are assured to notice
        # TODO deprecate usage of skill_name once mycroft catches up
        msm_skills = {skill.name: skill for skill in self.msm.all_skills}

        skill_ids = {os.path.basename(skill_path): skill_path
                     for skill_path in self._get_skill_directories()}
        priority_skills = self.skills_config.get("priority_skills", [])
        for skill_id in priority_skills:
            if skill_id in msm_skills and skill_id not in skill_ids:
                LOG.warning("ovos-core expects a skill_id in 'priority_skills'\n"
                            "support for skill_name will be removed in version 0.0.3\n"
                            "This is a bug in mycrof-core, skill_name is not deterministic!")
                skill = msm_skills[skill_id]
                if not skill.is_local:
                    try:
                        self.msm.install(skill)
                    except Exception:
                        LOG.exception(f'Downloading priority skill: {skill_id} failed')
                        continue
                skill_path = skill.path
            else:
                skill_path = skill_ids.get(skill_id)

            if skill_path is not None:
                loader = self._load_skill(skill_path)
                if loader:
                    self.upload_queue.put(loader)
            else:
                LOG.error(f'Priority skill {skill_id} can\'t be found')

        self._alive_status = True

    def run(self):
        """Load skills and update periodically from disk and internet."""
        self._remove_git_locks()
        if self.skills_config.get("wait_for_internet", True):
            while not connected() and not self._connected_event.is_set():
                sleep(1)
            self._connected_event.set()

        if (not self.skill_updater.defaults_installed() and
                self.skills_config["auto_update"]):
            LOG.info('Not all default skills are installed, '
                     'performing skill update...')
            self.skill_updater.update_skills()
        self._load_on_startup()

        # Sync backend and skills.
        if is_paired() and not self.upload_queue.started:
            self._start_settings_update()

        # Scan the file folder that contains Skills.  If a Skill is updated,
        # unload the existing version from memory and reload from the disk.
        while not self._stop_event.is_set():
            try:
                self._unload_removed_skills()
                self._reload_modified_skills()
                self._load_new_skills()
                self._update_skills()
                if (is_paired() and self.upload_queue.started and
                        len(self.upload_queue) > 0):
                    self.msm.clear_cache()
                    self.skill_updater.post_manifest()
                    self.upload_queue.send()

                self._watchdog()
                sleep(2)  # Pause briefly before beginning next scan
            except Exception:
                LOG.exception('Something really unexpected has occured '
                              'and the skill manager loop safety harness was '
                              'hit.')
                sleep(30)

    def _remove_git_locks(self):
        """If git gets killed from an abrupt shutdown it leaves lock files."""
        for skill_folder in _get_skill_locations():
            lock_path = os.path.join(skill_folder, '*/.git/index.lock')
            for i in glob(lock_path):
                LOG.warning('Found and removed git lock file: ' + i)
                os.remove(i)

    def _load_on_startup(self):
        """Handle initial skill load."""
        LOG.info('Loading installed skills...')
        self._load_new_skills()
        LOG.info("Skills all loaded!")
        self.bus.emit(Message('mycroft.skills.initialized'))
        self._loaded_status = True

    def _reload_modified_skills(self):
        """Handle reload of recently changed skill(s)"""
        for skill_dir in self._get_skill_directories():
            try:
                skill_loader = self.skill_loaders.get(skill_dir)
                if skill_loader is not None and skill_loader.reload_needed():
                    # If reload succeed add settingsmeta to upload queue
                    if skill_loader.reload():
                        self.upload_queue.put(skill_loader)
            except Exception:
                LOG.exception('Unhandled exception occured while '
                              'reloading {}'.format(skill_dir))

    def _load_new_skills(self):
        """Handle load of skills installed since startup."""
        for skill_dir in self._get_skill_directories():
            replaced_skills = []
            # by definition skill_id == folder name
            skill_id = os.path.basename(skill_dir)
            for old_skill_dir, skill_loader in self.skill_loaders.items():
                if old_skill_dir != skill_dir and \
                        skill_loader.skill_id == skill_id:
                    # a higher priority equivalent has been detected!
                    replaced_skills.append(old_skill_dir)

            for old_skill_dir in replaced_skills:
                # unload the old skill
                self._unload_skill(old_skill_dir)

            if skill_dir not in self.skill_loaders:
                loader = self._load_skill(skill_dir)
                if loader:
                    self.upload_queue.put(loader)

    def _load_skill(self, skill_directory):
        if not self.config["websocket"].get("shared_connection", True):
            # see BusBricker skill to understand why this matters
            # any skill can manipulate the bus from other skills
            # this patch ensures each skill gets it's own
            # connection that can't be manipulated by others
            # https://github.com/EvilJarbas/BusBrickerSkill
            bus = MessageBusClient(cache=True)
            bus.run_in_thread()
        else:
            bus = self.bus
        skill_loader = SkillLoader(bus, skill_directory)
        try:
            load_status = skill_loader.load()
        except Exception:
            LOG.exception('Load of skill {} failed!'.format(skill_directory))
            load_status = False
        finally:
            self.skill_loaders[skill_directory] = skill_loader

        return skill_loader if load_status else None

    def _unload_skill(self, skill_dir):
        if skill_dir in self.skill_loaders:
            skill = self.skill_loaders[skill_dir]
            LOG.info(f'removing {skill.skill_id}')
            try:
                skill.unload()
            except Exception:
                LOG.exception('Failed to shutdown skill ' + skill.id)
            del self.skill_loaders[skill_dir]

    def _get_skill_directories(self):
        # let's scan all valid directories, if a skill folder name exists in
        # more than one of these then it should override the previous
        skillmap = {}
        for skills_dir in _get_skill_locations():
            if not os.path.isdir(skills_dir):
                continue
            for skill_id in os.listdir(skills_dir):
                skill = os.path.join(skills_dir, skill_id)
                # NOTE: empty folders mean the skill should NOT be loaded
                if os.path.isdir(skill):
                    skillmap[skill_id] = skill

        for skill_id, skill_dir in skillmap.items():
            # TODO: all python packages must have __init__.py!  Better way?
            # check if folder is a skill (must have __init__.py)
            if SKILL_MAIN_MODULE in os.listdir(skill_dir):
                if skill_dir in self.empty_skill_dirs:
                    self.empty_skill_dirs.discard(skill_dir)
            else:
                if skill_dir not in self.empty_skill_dirs:
                    self.empty_skill_dirs.add(skill_dir)
                    LOG.debug('Found skills directory with no skill: ' +
                              skill_dir)

        return skillmap.values()

    def _unload_removed_skills(self):
        """Shutdown removed skills."""
        skill_dirs = self._get_skill_directories()
        # Find loaded skills that don't exist on disk
        removed_skills = [
            s for s in self.skill_loaders.keys() if s not in skill_dirs
        ]
        for skill_dir in removed_skills:
            self._unload_skill(skill_dir)

        # If skills were removed make sure to update the manifest on the
        # mycroft backend.
        if removed_skills:
            self.skill_updater.post_manifest(reload_skills_manifest=True)

    def _update_skills(self):
        """Update skills once an hour if update is enabled"""
        do_skill_update = (
                time() >= self.skill_updater.next_download and
                self.skills_config.get("auto_update", False)
        )
        if do_skill_update:
            self.skill_updater.update_skills()

    def is_alive(self, message=None):
        """Respond to is_alive status request."""
        return self._alive_status

    def is_all_loaded(self, message=None):
        """ Respond to all_loaded status request."""
        return self._loaded_status

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
                    LOG.info("Deactivating skill: " + skill_loader.skill_id)
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
        self.settings_downloader.stop_downloading()
        self.upload_queue.stop()

        # Do a clean shutdown of all skills
        for skill_loader in self.skill_loaders.values():
            if skill_loader.instance is not None:
                _shutdown_skill(skill_loader.instance)

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
                    # check the signature of a converse method
                    # to either pass a message or not
                    if len(signature(
                            skill_loader.instance.converse).parameters) == 1:
                        result = skill_loader.instance.converse(
                            message=message)
                    else:
                        utterances = message.data['utterances']
                        lang = message.data['lang']
                        result = skill_loader.instance.converse(
                            utterances=utterances, lang=lang)
                    self._emit_converse_response(result, message, skill_loader)
                except Exception:
                    error_message = 'exception in converse method'
                    LOG.exception(error_message)
                    self._emit_converse_error(message, skill_id, error_message)
                finally:
                    break

        if not skill_found:
            error_message = 'skill id does not exist'
            self._emit_converse_error(message, skill_id, error_message)

    def _emit_converse_error(self, message, skill_id, error_msg):
        """Emit a message reporting the error back to the intent service."""
        reply = message.reply('skill.converse.response',
                              data=dict(skill_id=skill_id, error=error_msg))
        self.bus.emit(reply)

    def _emit_converse_response(self, result, message, skill_loader):
        reply = message.reply(
            'skill.converse.response',
            data=dict(skill_id=skill_loader.skill_id, result=result)
        )
        self.bus.emit(reply)
