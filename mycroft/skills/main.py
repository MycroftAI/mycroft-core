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
import json
import subprocess
import sys
import time
from threading import Timer, Thread, Event, Lock
import gc

import os
from os.path import exists, join

import mycroft.dialog
import mycroft.lock
from mycroft import MYCROFT_ROOT_PATH
from mycroft.api import is_paired
from mycroft.configuration import Configuration
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.skills.core import load_skill, create_skill_descriptor, \
    MainModule, FallbackSkill
from mycroft.skills.event_scheduler import EventScheduler
from mycroft.skills.intent_service import IntentService
from mycroft.skills.padatious_service import PadatiousService
from mycroft.util import connected
from mycroft.util.log import LOG


ws = None
event_scheduler = None
skill_manager = None

DEBUG = Configuration.get().get("debug", False)
skills_config = Configuration.get().get("skills")
BLACKLISTED_SKILLS = skills_config.get("blacklisted_skills", [])
PRIORITY_SKILLS = skills_config.get("priority_skills", [])
SKILLS_DIR = '/opt/mycroft/skills'
AUTO_UPDATE = skills_config.get("auto_update", True)
installer_config = Configuration.get().get("SkillInstallerSkill")
MSM_BIN = installer_config.get("path", join(MYCROFT_ROOT_PATH, 'msm', 'msm'))

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
    skill_manager.start()

    # Wait until skills have been loaded once before starting to check
    # network connection
    skill_manager.wait_loaded_priority()
    check_connection()


def check_connection():
    """
        Check for network connection. If not paired trigger pairing.
        Runs as a Timer every second until connection is detected.
    """
    if connected():
        ws.emit(Message('mycroft.internet.connected'))
        # check for pairing, if not automatically start pairing
        if not is_paired():
            # begin the process
            payload = {
                'utterances': ["pair my device"],
                'lang': "en-us"
            }
            ws.emit(Message("recognizer_loop:utterance", payload))
        else:
            from mycroft.api import DeviceApi
            api = DeviceApi()
            api.update_version()
    else:
        thread = Timer(1, check_connection)
        thread.daemon = True
        thread.start()


def _get_last_modified_date(path):
    """
        Get last modified date excluding compiled python files, hidden
        directories and the settings.json file.

        Arg:
            path:   skill directory to check
        Returns:    time of last change
    """
    last_date = 0
    root_dir, subdirs, files = next(os.walk(path))
    # get subdirs and remove hidden ones
    subdirs = [s for s in subdirs if not s.startswith('.')]
    for subdir in subdirs:
        for root, _, _ in os.walk(join(path, subdir)):
            base = os.path.basename(root)
            # checking if is a hidden path
            if not base.startswith(".") and not base.startswith("/."):
                last_date = max(last_date, os.path.getmtime(root))

    # check files of interest in the skill root directory
    files = [f for f in files
             if not f.endswith('.pyc') and f != 'settings.json']
    for f in files:
        last_date = max(last_date, os.path.getmtime(os.path.join(path, f)))
    return last_date


class SkillManager(Thread):
    """ Load, update and manage instances of Skill on this system. """

    def __init__(self, ws):
        super(SkillManager, self).__init__()
        self._stop_event = Event()
        self._loaded_priority = Event()
        self.next_download = time.time() - 1    # download ASAP
        self.loaded_skills = {}
        self.msm_blocked = False
        self.ws = ws

        # Conversation management
        ws.on('skill.converse.request', self.handle_converse_request)

        # Update on initial connection
        ws.on('mycroft.internet.connected', self.schedule_update_skills)

        # Update upon request
        ws.on('skillmanager.update', self.schedule_update_skills)

        # Register handlers for external MSM signals
        ws.on('msm.updating', self.block_msm)
        ws.on('msm.removing', self.block_msm)
        ws.on('msm.installing', self.block_msm)
        ws.on('msm.updated', self.restore_msm)
        ws.on('msm.removed', self.restore_msm)
        ws.on('msm.installed', self.restore_msm)

        # when locked, MSM is active or intentionally blocked
        self.__msm_lock = Lock()
        self.__ext_lock = Lock()

    def schedule_update_skills(self, message=None):
        """ Schedule a skill update to take place directly. """
        # Update skills at next opportunity
        self.next_download = time.time() - 1

    def block_msm(self, message=None):
        """ Disallow start of msm. """

        # Make sure the external locking of __msm_lock is done in correct order
        with self.__ext_lock:
            if not self.msm_blocked:
                self.__msm_lock.acquire()
                self.msm_blocked = True

    def restore_msm(self, message=None):
        """ Allow start of msm if not allowed. """

        # Make sure the external locking of __msm_lock is done in correct order
        with self.__ext_lock:
            if self.msm_blocked:
                self.__msm_lock.release()
                self.msm_blocked = False

    def download_skills(self, speak=False):
        """ Invoke MSM to install default skills and/or update installed skills

            Args:
                speak (bool, optional): Speak the result? Defaults to False
        """
        if not AUTO_UPDATE:
            return

        # Don't invoke msm if already running
        if exists(MSM_BIN) and self.__msm_lock.acquire():
            try:
                # Invoke the MSM script to do the hard work.
                LOG.debug("==== Invoking Mycroft Skill Manager: " + MSM_BIN)
                p = subprocess.Popen(MSM_BIN + " default",
                                     stderr=subprocess.STDOUT,
                                     stdout=subprocess.PIPE, shell=True)
                (output, err) = p.communicate()
                res = p.returncode
                # Always set next update to an hour from now if successful
                if res == 0:
                    self.next_download = time.time() + 60 * MINUTES

                    if res == 0 and speak:
                        self.ws.emit(Message("speak", {'utterance':
                                     mycroft.dialog.get("skills updated")}))
                    return True
                elif not connected():
                    LOG.error('msm failed, network connection not available')
                    if speak:
                        self.ws.emit(Message("speak", {
                            'utterance': mycroft.dialog.get(
                                "not connected to the internet")}))
                    self.next_download = time.time() + 5 * MINUTES
                    return False
                elif res != 0:
                    LOG.error(
                        'msm failed with error {}: {}'.format(
                            res, output))
                    if speak:
                        self.ws.emit(Message("speak", {
                            'utterance': mycroft.dialog.get(
                                "sorry I couldn't install default skills")}))
                    self.next_download = time.time() + 5 * MINUTES
                    return False
            finally:
                self.__msm_lock.release()
        else:
            LOG.error("Unable to invoke Mycroft Skill Manager: " + MSM_BIN)

    def _load_or_reload_skill(self, skill_folder):
        """
            Check if unloaded skill or changed skill needs reloading
            and perform loading if necessary.
        """
        if skill_folder not in self.loaded_skills:
            self.loaded_skills[skill_folder] = {
                "id": hash(os.path.join(SKILLS_DIR, skill_folder))
            }
        skill = self.loaded_skills.get(skill_folder)
        skill["path"] = os.path.join(SKILLS_DIR, skill_folder)

        # check if folder is a skill (must have __init__.py)
        if not MainModule + ".py" in os.listdir(skill["path"]):
            return

        # getting the newest modified date of skill
        modified = _get_last_modified_date(skill["path"])
        last_mod = skill.get("last_modified", 0)

        # checking if skill is loaded and wasn't modified
        if skill.get("loaded") and modified <= last_mod:
            return

        # check if skill was modified
        elif skill.get("instance") and modified > last_mod:
            # check if skill is allowed to reloaded
            if not skill["instance"].reload_skill:
                return
            LOG.debug("Reloading Skill: " + skill_folder)
            # removing listeners and stopping threads
            skill["instance"].shutdown()

            if DEBUG:
                gc.collect()  # Collect garbage to remove false references
                # Remove two local references that are known
                refs = sys.getrefcount(skill["instance"]) - 2
                if refs > 0:
                    LOG.warning(
                        "After shutdown of {} there are still "
                        "{} references remaining. The skill "
                        "won't be cleaned from memory."
                        .format(skill['instance'].name, refs))
            del skill["instance"]

        # (Re)load the skill from disk
        with self.__msm_lock:  # Make sure msm isn't running
            skill["loaded"] = True
            desc = create_skill_descriptor(skill["path"])
            skill["instance"] = load_skill(desc,
                                           self.ws, skill["id"],
                                           BLACKLISTED_SKILLS)
            skill["last_modified"] = modified

    def load_skill_list(self, skills_to_load):
        """ Load the specified list of skills from disk

            Args:
                skills_to_load (list): list of skill directory names to load
        """
        if exists(SKILLS_DIR):
            # checking skills dir and getting all priority skills there
            skill_list = [folder for folder in filter(
                lambda x: os.path.isdir(os.path.join(SKILLS_DIR, x)),
                os.listdir(SKILLS_DIR)) if folder in skills_to_load]
            for skill_folder in skill_list:
                self._load_or_reload_skill(skill_folder)

    def run(self):
        """ Load skills and update periodically from disk and internet """

        # Load priority skills first, in order (very first time this will
        # occur before MSM has run)
        self.load_skill_list(PRIORITY_SKILLS)
        self._loaded_priority.set()

        # Scan the file folder that contains Skills.  If a Skill is updated,
        # unload the existing version from memory and reload from the disk.
        while not self._stop_event.is_set():
            # Update skills once an hour
            if time.time() >= self.next_download:
                self.download_skills()

            # Look for recently changed skill(s) needing a reload
            if exists(SKILLS_DIR):
                # checking skills dir and getting all skills there
                list = filter(lambda x: os.path.isdir(
                    os.path.join(SKILLS_DIR, x)), os.listdir(SKILLS_DIR))

                for skill_folder in list:
                    self._load_or_reload_skill(skill_folder)

            # remember the date of the last modified skill
            modified_dates = map(lambda x: x.get("last_modified"),
                                 self.loaded_skills.values())

            # Pause briefly before beginning next scan
            time.sleep(2)

        # Do a clean shutdown of all skills
        for skill in self.loaded_skills:
            try:
                self.loaded_skills[skill]['instance'].shutdown()
            except BaseException:
                pass

    def wait_loaded_priority(self):
        """ Block until all priority skills have loaded """
        while not self._loaded_priority.is_set():
            time.sleep(1)

    def stop(self):
        """ Tell the manager to shutdown """
        self._stop_event.set()

    def handle_converse_request(self, message):
        """ Check if the targeted skill id can handle conversation

        If supported, the conversation is invoked.
        """

        skill_id = int(message.data["skill_id"])
        utterances = message.data["utterances"]
        lang = message.data["lang"]

        # loop trough skills list and call converse for skill with skill_id
        for skill in self.loaded_skills:
            if self.loaded_skills[skill]["id"] == skill_id:
                try:
                    instance = self.loaded_skills[skill]["instance"]
                except BaseException:
                    LOG.error("converse requested but skill not loaded")
                    self.ws.emit(Message("skill.converse.response", {
                        "skill_id": 0, "result": False}))
                    return
                try:
                    result = instance.converse(utterances, lang)
                    self.ws.emit(Message("skill.converse.response", {
                        "skill_id": skill_id, "result": result}))
                    return
                except BaseException:
                    LOG.exception(
                        "Error in converse method for skill " + str(skill_id))
        self.ws.emit(Message("skill.converse.response",
                             {"skill_id": 0, "result": False}))


def main():
    global ws
    # Create PID file, prevent multiple instancesof this service
    mycroft.lock.Lock('skills')
    # Connect this Skill management process to the websocket
    ws = WebsocketClient()
    Configuration.init(ws)
    ignore_logs = Configuration.get().get("ignore_logs")

    # Listen for messages and echo them for logging
    def _echo(message):
        try:
            _message = json.loads(message)

            if _message.get("type") in ignore_logs:
                return

            if _message.get("type") == "registration":
                # do not log tokens from registration messages
                _message["data"]["token"] = None
            message = json.dumps(_message)
        except BaseException:
            pass
        LOG('SKILLS').debug(message)

    ws.on('message', _echo)
    # Startup will be called after websocket is fully live
    ws.once('open', _starting_up)
    ws.run_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if event_scheduler:
            event_scheduler.shutdown()

        # Terminate all running threads that update skills
        if skill_manager:
            skill_manager.stop()
            skill_manager.join()

    finally:
        sys.exit()
