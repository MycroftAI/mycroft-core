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
import gc
import os
import sys
import time
from glob import glob
from itertools import chain

from os.path import exists, join, basename, dirname, expanduser, isfile
from threading import Timer, Thread, Event

import mycroft.lock
from msm import MycroftSkillsManager, SkillRepo, MsmException
from mycroft import dialog
from mycroft.api import is_paired, BackendDown
from mycroft.client.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.skills.core import load_skill, create_skill_descriptor, \
    MainModule, FallbackSkill
from mycroft.skills.event_scheduler import EventScheduler
from mycroft.skills.intent_service import IntentService
from mycroft.skills.padatious_service import PadatiousService
from mycroft.util import (
    connected, wait_while_speaking, reset_sigint_handler,
    create_echo_function, create_daemon, wait_for_exit_signal
)
from mycroft.util.log import LOG

ws = None
event_scheduler = None
skill_manager = None

# Remember "now" at startup.  Used to detect clock changes.
start_ticks = time.monotonic()
start_clock = time.time()

DEBUG = Configuration.get().get("debug", False)
skills_config = Configuration.get().get("skills")
BLACKLISTED_SKILLS = skills_config.get("blacklisted_skills", [])
PRIORITY_SKILLS = skills_config.get("priority_skills", [])

installer_config = Configuration.get().get("SkillInstallerSkill")

MINUTES = 60  # number of seconds in a minute (syntatic sugar)


def connect():
    global ws
    ws.run_forever()


def _starting_up():
    """
        Start loading skills.

        Starts
        - SkillManager to load/reloading of skills when needed
        - a timer to check for internet connection
        - adapt intent service
        - padatious intent service
    """
    global ws, skill_manager, event_scheduler

    ws.on('intent_failure', FallbackSkill.make_intent_failure_handler(ws))

    # Create the Intent manager, which converts utterances to intents
    # This is the heart of the voice invoked skill system

    service = IntentService(ws)
    PadatiousService(ws, service)
    event_scheduler = EventScheduler(ws)

    # Create a thread that monitors the loaded skills, looking for updates
    skill_manager = SkillManager(ws)
    skill_manager.daemon = True
    # Wait until skills have been loaded once before starting to check
    # network connection
    skill_manager.load_priority()
    skill_manager.start()
    check_connection()


def check_connection():
    """
        Check for network connection. If not paired trigger pairing.
        Runs as a Timer every second until connection is detected.
    """
    if connected():
        enclosure = EnclosureAPI(ws)

        if is_paired():
            # Skip the sync message when unpaired because the prompt to go to
            # home.mycrof.ai will be displayed by the pairing skill
            enclosure.mouth_text(dialog.get("message_synching.clock"))

        # Force a sync of the local clock with the internet
        config = Configuration.get()
        platform = config['enclosure'].get("platform", "unknown")
        if platform in ['mycroft_mark_1', 'picroft']:
            ws.emit(Message("system.ntp.sync"))
            time.sleep(15)  # TODO: Generate/listen for a message response...

        # Check if the time skewed significantly.  If so, reboot
        skew = abs((time.monotonic() - start_ticks) -
                   (time.time() - start_clock))
        if skew > 60 * 60:
            # Time moved by over an hour in the NTP sync. Force a reboot to
            # prevent weird things from occcurring due to the 'time warp'.
            #
            data = {'utterance': dialog.get("time.changed.reboot")}
            ws.emit(Message("speak", data))
            wait_while_speaking()

            # provide visual indicators of the reboot
            enclosure.mouth_text(dialog.get("message_rebooting"))
            enclosure.eyes_color(70, 65, 69)  # soft gray
            enclosure.eyes_spin()

            # give the system time to finish processing enclosure messages
            time.sleep(1.0)

            # reboot
            ws.emit(Message("system.reboot"))
            return
        else:
            ws.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)

        ws.emit(Message('mycroft.internet.connected'))
        # check for pairing, if not automatically start pairing
        try:
            if not is_paired(ignore_errors=False):
                payload = {
                    'utterances': ["pair my device"],
                    'lang': "en-us"
                }
                ws.emit(Message("recognizer_loop:utterance", payload))
            else:
                from mycroft.api import DeviceApi
                api = DeviceApi()
                api.update_version()
        except BackendDown:
            data = {'utterance': dialog.get("backend.down")}
            ws.emit(Message("speak", data))
            ws.emit(Message("backend.down"))

    else:
        thread = Timer(1, check_connection)
        thread.daemon = True
        thread.start()


def _get_last_modified_date(path):
    """
        Get last modified date excluding compiled python files, hidden
        directories and the settings.json file.

        Args:
            path:   skill directory to check

        Returns:
            int: time of last change
    """
    all_files = []
    for root_dir, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if (not f.endswith('.pyc') and f != 'settings.json' and
                    not f.startswith('.')):
                all_files.append(join(root_dir, f))
    # check files of interest in the skill root directory
    return max(os.path.getmtime(f) for f in all_files)


class SkillManager(Thread):
    """ Load, update and manage instances of Skill on this system. """

    def __init__(self, ws):
        super(SkillManager, self).__init__()
        self._stop_event = Event()
        self._connected_event = Event()

        self.loaded_skills = {}
        self.ws = ws
        self.enclosure = EnclosureAPI(ws)

        # Schedule install/update of default skill
        self.msm = self.create_msm()
        self.num_install_retries = 0

        self.update_interval = Configuration.get()['skills']['update_interval']
        self.update_interval = int(self.update_interval * 60 * MINUTES)
        self.dot_msm = join(self.msm.skills_dir, '.msm')
        if exists(self.dot_msm):
            self.next_download = os.path.getmtime(self.dot_msm) + \
                                 self.update_interval
        else:
            self.next_download = time.time() - 1

        # Conversation management
        ws.on('skill.converse.request', self.handle_converse_request)

        # Update on initial connection
        ws.on('mycroft.internet.connected',
              lambda x: self._connected_event.set())

        # Update upon request
        ws.on('skillmanager.update', self.schedule_now)
        ws.on('skillmanager.list', self.send_skill_list)

    @staticmethod
    def create_msm():
        config = Configuration.get()
        msm_config = config['skills']['msm']
        repo_config = msm_config['repo']
        data_dir = expanduser(config['data_dir'])
        skills_dir = join(data_dir, msm_config['directory'])
        repo_cache = join(data_dir, repo_config['cache'])
        platform = config['enclosure'].get('platform', 'default')
        return MycroftSkillsManager(
            platform=platform, skills_dir=skills_dir,
            repo=SkillRepo(
                repo_cache, repo_config['url'], repo_config['branch']
            ), versioned=msm_config['versioned']
        )

    def schedule_now(self, message=None):
        self.next_download = time.time() - 1

    @property
    def installed_skills_file(self):
        venv = dirname(dirname(sys.executable))
        if os.access(venv, os.W_OK | os.R_OK | os.X_OK):
            return join(venv, '.mycroft-skills')
        return expanduser('~/.mycroft/.mycroft-skills')

    def load_installed_skills(self) -> set:
        skills_file = self.installed_skills_file
        if not isfile(skills_file):
            return set()
        with open(skills_file) as f:
            return {
                i.strip() for i in f.read().split('\n') if i.strip()
            }

    def save_installed_skills(self, skill_names):
        with open(self.installed_skills_file, 'w') as f:
            f.write('\n'.join(skill_names))

    def download_skills(self, speak=False):
        """ Invoke MSM to install default skills and/or update installed skills

            Args:
                speak (bool, optional): Speak the result? Defaults to False
        """
        if not connected():
            LOG.error('msm failed, network connection not available')
            if speak:
                self.ws.emit(Message("speak", {
                    'utterance': dialog.get(
                        "not connected to the internet")}))
            self.next_download = time.time() + 5 * MINUTES
            return False

        installed_skills = self.load_installed_skills()
        default_groups = dict(self.msm.repo.get_default_skill_names())
        default_names = set(chain(default_groups['default'],
                                  default_groups[self.msm.platform]))

        default_skill_errored = False

        def install_or_update(skill):
            """Install missing defaults and update existing skills"""
            if skill.is_local:
                skill.update()
                if skill.name not in installed_skills:
                    skill.update_deps()
            elif skill.name in default_names:
                try:
                    skill.install()
                except Exception:
                    if skill.name in default_names:
                        LOG.warning(
                            'Failed to install default skill: ' + skill.name
                        )
                        nonlocal default_skill_errored
                        default_skill_errored = True
                    raise
            installed_skills.add(skill.name)

        try:
            self.msm.apply(install_or_update, self.msm.list())
        except MsmException as e:
            LOG.error('Failed to update skills: {}'.format(repr(e)))

        self.save_installed_skills(installed_skills)

        if speak:
            data = {'utterance': dialog.get("skills updated")}
            self.ws.emit(Message("speak", data))

        if default_skill_errored and self.num_install_retries < 10:
            self.num_install_retries += 1
            self.next_download = time.time() + 5 * MINUTES
            return False
        self.num_install_retries = 0

        with open(self.dot_msm, 'a'):
            os.utime(self.dot_msm, None)
        self.next_download = time.time() + self.update_interval

        return True

    def _load_or_reload_skill(self, skill_path):
        """
            Check if unloaded skill or changed skill needs reloading
            and perform loading if necessary.

            Returns True if the skill was loaded/reloaded
        """
        skill_path = skill_path.rstrip('/')
        skill = self.loaded_skills.setdefault(skill_path, {})
        skill.update({
            "id": basename(skill_path),
            "path": skill_path
        })

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
            if not skill["instance"].reload_skill:
                return False

            LOG.debug("Reloading Skill: " + basename(skill_path))
            # removing listeners and stopping threads
            try:
                skill["instance"]._shutdown()
            except Exception:
                LOG.exception("An error occured while shutting down {}"
                              .format(skill["instance"].name))

            if DEBUG:
                gc.collect()  # Collect garbage to remove false references
                # Remove two local references that are known
                refs = sys.getrefcount(skill["instance"]) - 2
                if refs > 0:
                    msg = ("After shutdown of {} there are still "
                           "{} references remaining. The skill "
                           "won't be cleaned from memory.")
                    LOG.warning(msg.format(skill['instance'].name, refs))
            del skill["instance"]
            self.ws.emit(Message("mycroft.skills.shutdown",
                                 {"path": skill_path,
                                  "id": skill["id"]}))

        skill["loaded"] = True
        desc = create_skill_descriptor(skill_path)
        skill["instance"] = load_skill(desc,
                                       self.ws, skill["id"],
                                       BLACKLISTED_SKILLS)
        skill["last_modified"] = modified
        if skill['instance'] is not None:
            self.ws.emit(Message('mycroft.skills.loaded',
                                 {'path': skill_path,
                                  'id': skill['id'],
                                  'name': skill['instance'].name,
                                  'modified': modified}))
            return True
        else:
            self.ws.emit(Message('mycroft.skills.loading_failure',
                                 {'path': skill_path,
                                  'id': skill['id']}))
        return False

    def load_priority(self):
        skills = {skill.name: skill for skill in self.msm.list()}
        for skill_name in PRIORITY_SKILLS:
            skill = skills[skill_name]
            if not skill.is_local:
                try:
                    skill.install()
                except Exception:
                    LOG.exception('Downloading priority skill:' + skill.name)
                    if not skill.is_local:
                        continue
            self._load_or_reload_skill(skill.path)

    def run(self):
        """ Load skills and update periodically from disk and internet """

        # Load priority skills first, in order (very first time this will
        # occur before MSM has run)

        self._connected_event.wait()
        has_loaded = False

        # check if skill updates are enabled
        update = Configuration.get()["skills"]["auto_update"]

        # Scan the file folder that contains Skills.  If a Skill is updated,
        # unload the existing version from memory and reload from the disk.
        while not self._stop_event.is_set():
            # Update skills once an hour if update is enabled
            if time.time() >= self.next_download and update:
                self.download_skills()

            # Look for recently changed skill(s) needing a reload
            # checking skills dir and getting all skills there
            skill_paths = glob(join(self.msm.skills_dir, '*/'))
            still_loading = False
            for skill_path in skill_paths:
                still_loading = (
                        self._load_or_reload_skill(skill_path) or
                        still_loading
                )
            if not has_loaded and not still_loading and len(skill_paths) > 0:
                has_loaded = True
                self.ws.emit(Message('mycroft.skills.initialized'))

            # Pause briefly before beginning next scan
            time.sleep(2)

    def send_skill_list(self, message=None):
        """
            Send list of loaded skills.
        """
        try:
            self.ws.emit(Message('mycroft.skills.list', data={'skills': [
                basename(skill_path) for skill_path in self.loaded_skills
            ]}))
        except Exception as e:
            LOG.exception(e)

    def stop(self):
        """ Tell the manager to shutdown """
        self._stop_event.set()

        # Do a clean shutdown of all skills
        for name, skill_info in self.loaded_skills.items():
            instance = skill_info.get('instance')
            if instance:
                try:
                    instance._shutdown()
                except Exception:
                    LOG.exception('Shutting down skill: ' + name)

    def handle_converse_request(self, message):
        """ Check if the targeted skill id can handle conversation

        If supported, the conversation is invoked.
        """

        skill_id = message.data["skill_id"]
        utterances = message.data["utterances"]
        lang = message.data["lang"]

        # loop trough skills list and call converse for skill with skill_id
        for skill in self.loaded_skills:
            if self.loaded_skills[skill]["id"] == skill_id:
                try:
                    instance = self.loaded_skills[skill]["instance"]
                except BaseException:
                    LOG.error("converse requested but skill not loaded")
                    self.ws.emit(message.reply("skill.converse.response", {
                        "skill_id": 0, "result": False}))
                    return
                try:
                    result = instance.converse(utterances, lang)
                    self.ws.emit(message.reply("skill.converse.response", {
                        "skill_id": skill_id, "result": result}))
                    return
                except BaseException:
                    LOG.exception(
                        "Error in converse method for skill " + str(skill_id))
        self.ws.emit(message.reply("skill.converse.response",
                                   {"skill_id": 0, "result": False}))


def main():
    global ws
    reset_sigint_handler()
    # Create PID file, prevent multiple instancesof this service
    mycroft.lock.Lock('skills')
    # Connect this Skill management process to the websocket
    ws = WebsocketClient()
    Configuration.init(ws)

    ws.on('message', create_echo_function('SKILLS'))
    # Startup will be called after websocket is fully live
    ws.once('open', _starting_up)

    create_daemon(ws.run_forever)
    wait_for_exit_signal()
    shutdown()


def shutdown():
    if event_scheduler:
        event_scheduler.shutdown()

    # Terminate all running threads that update skills
    if skill_manager:
        skill_manager.stop()
        skill_manager.join()


if __name__ == "__main__":
    main()
