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
from os.path import basename
from glob import glob
from threading import Thread, Event, Lock
from time import sleep, monotonic
from mycroft.util.process_utils import ProcessStatus, StatusCallbackMap, ProcessState


from mycroft.api import is_paired
from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
from mycroft.util import connected
from mycroft.skills.settings import SkillSettingsDownloader
from mycroft.skills.skill_loader import get_skill_directories, SkillLoader, PluginSkillLoader, find_skill_plugins
from mycroft.skills.skill_updater import SkillUpdater
from mycroft.messagebus import MessageBusClient

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
            LOG.warning(f'{instance.skill_id} shutdown took {shutdown_time} seconds')
    except Exception:
        LOG.exception(f'Failed to shut down skill: {instance.skill_id}')


def on_started():
    LOG.info('Skills Manager is starting up.')


def on_alive():
    LOG.info('Skills Manager is alive.')


def on_ready():
    LOG.info('Skills Manager is ready.')


def on_error(e='Unknown'):
    LOG.info(f'Skills Manager failed to launch ({e})')


def on_stopping():
    LOG.info('Skills Manager is shutting down...')


class SkillManager(Thread):

    def __init__(self, bus, watchdog=None, alive_hook=on_alive, started_hook=on_started, ready_hook=on_ready,
         error_hook=on_error, stopping_hook=on_stopping):
        """Constructor

        Args:
            bus (event emitter): Mycroft messagebus connection
            watchdog (callable): optional watchdog function
        """
        super(SkillManager, self).__init__()
        self.bus = bus
        # Set watchdog to argument or function returning None
        self._watchdog = watchdog or (lambda: None)
        callbacks = StatusCallbackMap(on_started=started_hook,
                                      on_alive=alive_hook,
                                      on_ready=ready_hook,
                                      on_error=error_hook,
                                      on_stopping=stopping_hook)
        self.status = ProcessStatus('skills', callback_map=callbacks)
        self.status.set_started()

        self._stop_event = Event()
        self._connected_event = Event()
        self.config = Configuration.get()
        self.upload_queue = UploadQueue()

        self.skill_loaders = {}
        self.plugin_skills = {}
        self.enclosure = EnclosureAPI(bus)
        self.initial_load_complete = False
        self.num_install_retries = 0
        self.settings_downloader = SkillSettingsDownloader(self.bus)

        self.empty_skill_dirs = set()  # Save a record of empty skill dirs.

        self.skill_updater = SkillUpdater()
        self._define_message_bus_events()
        self.daemon = True

        self.status.bind(self.bus)

    def _define_message_bus_events(self):
        """Define message bus events with handlers defined in this class."""
        # Update on initial connection
        self.bus.on(
            'mycroft.internet.connected',
            lambda x: self._connected_event.set()
        )

        # Update upon request
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
            response = self.bus.wait_for_response(
                Message(f'mycroft.{ser}.is_ready'))
            if response and response.data['status']:
                services[ser] = True
        return all([services[ser] for ser in services])

    @property
    def skills_config(self):
        return self.config['skills']

    @property
    def msm(self):
        """DEPRECATED: do not use, method only for api backwards compatibility
        Logs a warning and returns None
        """
        return None

    @staticmethod
    def create_msm():
        """DEPRECATED: do not use, method only for api backwards compatibility
        Logs a warning and returns None
        """
        return None

    def schedule_now(self, _):
        """DEPRECATED: do not use, method only for api backwards compatibility
        Logs a warning
        """

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

    def load_plugin_skills(self):
        plugins = find_skill_plugins()
        loaded_skill_ids = [basename(p) for p in self.skill_loaders]
        for skill_id, plug in plugins.items():
            if skill_id not in self.plugin_skills and skill_id not in loaded_skill_ids:
                self._load_plugin_skill(skill_id, plug)

    def _load_plugin_skill(self, skill_id, skill_plugin):
        skill_loader = PluginSkillLoader(self.bus, skill_id)
        try:
            load_status = skill_loader.load(skill_plugin)
        except Exception:
            LOG.exception(f'Load of skill {skill_id} failed!')
            load_status = False
        finally:
            self.plugin_skills[skill_id] = skill_loader

        return skill_loader if load_status else None

    def load_priority(self):
        skill_ids = {os.path.basename(skill_path): skill_path
                     for skill_path in self._get_skill_directories()}
        priority_skills = self.skills_config.get("priority_skills") or []
        for skill_id in priority_skills:
            skill_path = skill_ids.get(skill_id)
            if skill_path is not None:
                loader = self._load_skill(skill_path)
                if loader:
                    self.upload_queue.put(loader)
            else:
                LOG.error(f'Priority skill {skill_id} can\'t be found')

        self.status.set_alive()

    def run(self):
        """Load skills and update periodically from disk and internet."""
        self._remove_git_locks()

        self.load_priority()

        if self.skills_config.get("wait_for_internet", True):
            while not connected() and not self._connected_event.is_set():
                sleep(1)
            self._connected_event.set()

        self._load_on_startup()

        # Sync backend and skills.
        if is_paired() and not self.upload_queue.started:
            self.skill_updater.post_manifest()
            self._start_settings_update()

        self.status.set_ready()
        # Scan the file folder that contains Skills.  If a Skill is updated,
        # unload the existing version from memory and reload from the disk.
        while not self._stop_event.is_set():
            try:
                self._unload_removed_skills()
                self._reload_modified_skills()
                self._load_new_skills()
                self._watchdog()
                sleep(2)  # Pause briefly before beginning next scan
            except Exception:
                LOG.exception('Something really unexpected has occured '
                              'and the skill manager loop safety harness was '
                              'hit.')
                sleep(30)

    def _remove_git_locks(self):
        """If git gets killed from an abrupt shutdown it leaves lock files."""
        for skills_dir in get_skill_directories():
            lock_path = os.path.join(skills_dir, '*/.git/index.lock')
            for i in glob(lock_path):
                LOG.warning('Found and removed git lock file: ' + i)
                os.remove(i)

    def _load_on_startup(self):
        """Handle initial skill load."""
        self.load_plugin_skills()
        LOG.info('Loading installed skills...')
        self._load_new_skills()
        LOG.info("Skills all loaded!")
        self.bus.emit(Message('mycroft.skills.initialized'))

    def _reload_modified_skills(self):
        """Handle reload of recently changed skill(s)"""
        for skill_dir, skill_loader in self.skill_loaders.items():
            try:
                if skill_loader is not None and skill_loader.reload_needed():
                    # If reload succeed add settingsmeta to upload queue
                    if skill_loader.reload():
                        self.upload_queue.put(skill_loader)
            except Exception:
                LOG.exception(f'Unhandled exception occured while reloading {skill_dir}')

    def _load_new_skills(self):
        """Handle load of skills installed since startup."""
        for skill_dir in self._get_skill_directories():
            replaced_skills = []
            # by definition skill_id == folder name
            skill_id = os.path.basename(skill_dir)

            # a local source install is replacing this plugin, unload it!
            if skill_id in self.plugin_skills:
                LOG.info(f"{skill_id} plugin will be replaced by a local version: {skill_dir}")
                self._unload_plugin_skill(skill_id)

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
            LOG.exception(f'Load of skill {skill_directory} failed!')
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
        for skills_dir in get_skill_directories():
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

    def _unload_plugin_skill(self, skill_id):
        if skill_id in self.plugin_skills:
            LOG.info('Unloading plugin skill: ' + skill_id)
            skill_loader = self.plugin_skills[skill_id]
            if skill_loader.instance is not None:
                try:
                    skill_loader.instance.default_shutdown()
                except Exception:
                    LOG.exception('Failed to shutdown plugin skill: ' + skill_loader.skill_id)
            self.plugin_skills.pop(skill_id)

    def is_alive(self, message=None):
        """Respond to is_alive status request."""
        return self.status.state >= ProcessState.ALIVE

    def is_all_loaded(self, message=None):
        """ Respond to all_loaded status request."""
        return self.status.state == ProcessState.READY

    def send_skill_list(self, _):
        """Send list of loaded skills."""
        try:
            message_data = {}
            # TODO handle external skills, OVOSAbstractApp/Hivemind skills are not accounted for
            skills = {**self.skill_loaders, **self.plugin_skills}

            for skill_loader in skills.values():
                message_data[skill_loader.skill_id] = {
                    "active": skill_loader.active and skill_loader.loaded,
                    "id": skill_loader.skill_id}

            self.bus.emit(Message('mycroft.skills.list', data=message_data))
        except Exception:
            LOG.exception('Failed to send skill list')

    def deactivate_skill(self, message):
        """Deactivate a skill."""
        try:
            # TODO handle external skills, OVOSAbstractApp/Hivemind skills are not accounted for
            skills = {**self.skill_loaders, **self.plugin_skills}
            for skill_loader in skills.values():
                if message.data['skill'] == skill_loader.skill_id:
                    LOG.info("Deactivating skill: " + skill_loader.skill_id)
                    skill_loader.deactivate()
        except Exception:
            LOG.exception('Failed to deactivate ' + message.data['skill'])

    def deactivate_except(self, message):
        """Deactivate all skills except the provided."""
        try:
            skill_to_keep = message.data['skill']
            LOG.info(f'Deactivating all skills except {skill_to_keep}')
            # TODO handle external skills, OVOSAbstractApp/Hivemind skills are not accounted for
            skills = {**self.skill_loaders, **self.plugin_skills}
            for skill in skills.values():
                if skill.skill_id != skill_to_keep:
                    skill.deactivate()
            LOG.info('Couldn\'t find skill ' + message.data['skill'])
        except Exception:
            LOG.exception('An error occurred during skill deactivation!')

    def activate_skill(self, message):
        """Activate a deactivated skill."""
        try:
            # TODO handle external skills, OVOSAbstractApp/Hivemind skills are not accounted for
            skills = {**self.skill_loaders, **self.plugin_skills}
            for skill_loader in skills.values():
                if (message.data['skill'] in ('all', skill_loader.skill_id)
                        and not skill_loader.active):
                    skill_loader.activate()
        except Exception:
            LOG.exception('Couldn\'t activate skill')

    def stop(self):
        """Tell the manager to shutdown."""
        self.status.set_stopping()
        self._stop_event.set()
        self.settings_downloader.stop_downloading()
        self.upload_queue.stop()

        # Do a clean shutdown of all skills
        for skill_loader in self.skill_loaders.values():
            if skill_loader.instance is not None:
                _shutdown_skill(skill_loader.instance)

        # Do a clean shutdown of all plugin skills
        for skill_id in self.plugin_skills:
            self._unload_plugin_skill(skill_id)
