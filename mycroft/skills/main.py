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
from threading import Timer, Thread, Event

import os
from os.path import exists, join

import mycroft.dialog
from mycroft import MYCROFT_ROOT_PATH
from mycroft.api import is_paired
from mycroft.configuration import ConfigurationManager
from mycroft.lock import Lock  # Creates PID file for single instance
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
loaded_skills = {}
last_modified_skill = 0
skill_reload_thread = None
skills_manager_timer = None

skills_config = ConfigurationManager.instance().get("skills")
BLACKLISTED_SKILLS = skills_config.get("blacklisted_skills", [])
PRIORITY_SKILLS = skills_config.get("priority_skills", [])

# SKILLS_DIR = "/home/guy/github/mycroft/mycroft-skills-mirror"
SKILLS_DIR = '/opt/mycroft/skills'

installer_config = ConfigurationManager.instance().get("SkillInstallerSkill")
MSM_BIN = installer_config.get("path", join(MYCROFT_ROOT_PATH, 'msm', 'msm'))


def connect():
    global ws
    ws.run_forever()


def install_default_skills(speak=True):
    """
        Install default skill set using msm.

        Args:
            speak (optional): Enable response for success. Default True
    """
    if exists(MSM_BIN):
        p = subprocess.Popen(MSM_BIN + " default", stderr=subprocess.STDOUT,
                             stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        res = p.returncode
        if res == 0 and speak:
            # ws.emit(Message("speak", {
            #     'utterance': mycroft.dialog.get("skills updated")}))
            pass
        elif not connected():
            LOG.error('msm failed, network connection is not available')
            ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("no network connection")}))
        elif res != 0:
            LOG.error('msm failed with error {}: {}'.format(res, output))
            ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get(
                    "sorry I couldn't install default skills")}))

    else:
        LOG.error("Unable to invoke Mycroft Skill Manager: " + MSM_BIN)


def skills_manager(message):
    """
        skills_manager runs on a Timer every hour and checks for updated
        skills.
    """
    global skills_manager_timer

    if connected():
        if skills_manager_timer is None:
            pass
        # Install default skills and look for updates via Github
        LOG.debug("==== Invoking Mycroft Skill Manager: " + MSM_BIN)
        install_default_skills(False)

    # Perform check again once and hour
    skills_manager_timer = Timer(3600, _skills_manager_dispatch)
    skills_manager_timer.daemon = True
    skills_manager_timer.start()


def _skills_manager_dispatch():
    """
        Thread function to trigger skill_manager over message bus.
    """
    global ws
    ws.emit(Message("skill_manager", {}))


def _starting_up():
    """
        Start loading skills.

        Starts
        - reloading of skills when needed
        - a timer to check for internet connection
        - a timer for updating skills every hour
        - adapt intent service
        - padatious intent service
    """
    global ws, skill_reload_thread, event_scheduler

    ws.on('intent_failure', FallbackSkill.make_intent_failure_handler(ws))

    # Create skill_manager listener and invoke the first time
    ws.on('skill_manager', skills_manager)
    ws.on('mycroft.internet.connected', install_default_skills)
    ws.emit(Message('skill_manager', {}))

    # Create the Intent manager, which converts utterances to intents
    # This is the heart of the voice invoked skill system

    PadatiousService(ws)
    IntentService(ws)
    event_scheduler = EventScheduler(ws)
    # Create a thread that monitors the loaded skills, looking for updates
    skill_reload_thread = WatchSkills()
    skill_reload_thread.daemon = True
    skill_reload_thread.start()

    # Wait until skills have been loaded once before starting to check
    # network connection
    skill_reload_thread.wait_loaded_priority()
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
    root_dir, subdirs, files = os.walk(path).next()
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


def load_skill_list(skills_to_load):
    """
        load list of specific skills.

        Args:
            skills_to_load (list): list of skill directories to load
    """
    if exists(SKILLS_DIR):
        # checking skills dir and getting all priority skills there
        skill_list = [folder for folder in filter(
            lambda x: os.path.isdir(os.path.join(SKILLS_DIR, x)),
            os.listdir(SKILLS_DIR)) if folder in skills_to_load]
        for skill_folder in skill_list:
            skill = {"id": hash(os.path.join(SKILLS_DIR, skill_folder))}
            skill["path"] = os.path.join(SKILLS_DIR, skill_folder)
            # checking if is a skill
            if not MainModule + ".py" in os.listdir(skill["path"]):
                continue
            # getting the newest modified date of skill
            last_mod = _get_last_modified_date(skill["path"])
            skill["last_modified"] = last_mod
            # loading skill
            skill["loaded"] = True
            skill["instance"] = load_skill(
                create_skill_descriptor(skill["path"]),
                ws, skill["id"])
            loaded_skills[skill_folder] = skill


class WatchSkills(Thread):
    """
        Thread function to reload skills when a change is detected.
    """

    def __init__(self):
        super(WatchSkills, self).__init__()
        self._stop_event = Event()
        self._loaded_once = Event()
        self._loaded_priority = Event()

    def run(self):
        global ws, loaded_skills, last_modified_skill

        # Load priority skills first by order
        load_skill_list(PRIORITY_SKILLS)
        self._loaded_priority.set()

        # Scan the file folder that contains Skills.  If a Skill is updated,
        # unload the existing version from memory and reload from the disk.
        while not self._stop_event.is_set():
            if exists(SKILLS_DIR):
                # checking skills dir and getting all skills there
                list = filter(lambda x: os.path.isdir(
                    os.path.join(SKILLS_DIR, x)), os.listdir(SKILLS_DIR))

                for skill_folder in list:
                    if skill_folder not in loaded_skills:
                        loaded_skills[skill_folder] = {
                            "id": hash(os.path.join(SKILLS_DIR, skill_folder))
                        }
                    skill = loaded_skills.get(skill_folder)
                    skill["path"] = os.path.join(SKILLS_DIR, skill_folder)
                    # checking if is a skill
                    if not MainModule + ".py" in os.listdir(skill["path"]):
                        continue
                    # getting the newest modified date of skill
                    last_mod = _get_last_modified_date(skill["path"])
                    skill["last_modified"] = last_mod
                    modified = skill.get("last_modified", 0)
                    # checking if skill is loaded and wasn't modified
                    if skill.get(
                            "loaded") and modified <= last_modified_skill:
                        continue
                    # checking if skill was modified
                    elif (skill.get("instance") and modified >
                            last_modified_skill):
                        # checking if skill should be reloaded
                        if not skill["instance"].reload_skill:
                            continue
                        LOG.debug("Reloading Skill: " + skill_folder)
                        # removing listeners and stopping threads
                        skill["instance"].shutdown()

                        # -2 since two local references that are known
                        refs = sys.getrefcount(skill["instance"]) - 2
                        if refs > 0:
                            LOG.warning(
                                "After shutdown of {} there are still "
                                "{} references remaining. The skill "
                                "won't be cleaned from memory."
                                .format(skill['instance'].name, refs))
                        del skill["instance"]
                    skill["loaded"] = True
                    skill["instance"] = load_skill(
                        create_skill_descriptor(skill["path"]),
                        ws, skill["id"],
                        BLACKLISTED_SKILLS)
            # get the last modified skill
            modified_dates = map(lambda x: x.get("last_modified"),
                                 loaded_skills.values())
            if len(modified_dates) > 0:
                last_modified_skill = max(modified_dates)

            if not self._loaded_once.is_set():
                self._loaded_once.set()
            # Pause briefly before beginning next scan
            time.sleep(2)

    def wait_loaded_priority(self):
        """
            Block until priority skills have loaded
        """
        while not self._loaded_priority.is_set():
            time.sleep(1)

    def wait_loaded_once(self):
        """
            Block until skills have loaded at least once.
        """
        while not self._loaded_once.is_set():
            time.sleep(1)

    def stop(self):
        """
            Stop the thread.
        """
        self._stop_event.set()


def handle_converse_request(message):
    """
        handle_converse_request checks if the targeted skill id can handle
        conversation.
    """
    skill_id = int(message.data["skill_id"])
    utterances = message.data["utterances"]
    lang = message.data["lang"]
    global ws, loaded_skills
    # loop trough skills list and call converse for skill with skill_id
    for skill in loaded_skills:
        if loaded_skills[skill]["id"] == skill_id:
            try:
                instance = loaded_skills[skill]["instance"]
            except:
                LOG.error("converse requested but skill not loaded")
                ws.emit(Message("skill.converse.response", {
                    "skill_id": 0, "result": False}))
                return
            try:
                result = instance.converse(utterances, lang)
                ws.emit(Message("skill.converse.response", {
                    "skill_id": skill_id, "result": result}))
                return
            except:
                LOG.error(
                    "Converse method malformed for skill " + str(skill_id))
    ws.emit(Message("skill.converse.response",
                    {"skill_id": 0, "result": False}))


def main():
    global ws
    lock = Lock('skills')  # prevent multiple instances of this service

    # Connect this Skill management process to the websocket
    ws = WebsocketClient()
    ConfigurationManager.init(ws)

    ignore_logs = ConfigurationManager.instance().get("ignore_logs")

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
        except:
            pass
        LOG('SKILLS').debug(message)

    ws.on('message', _echo)
    ws.on('skill.converse.request', handle_converse_request)
    # Startup will be called after websocket is full live
    ws.once('open', _starting_up)
    ws.run_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if event_scheduler:
            event_scheduler.shutdown()
        # Do a clean shutdown of all skills and terminate all running threads
        for skill in loaded_skills:
            try:
                loaded_skills[skill]['instance'].shutdown()
            except:
                pass
        if skills_manager_timer:
            skills_manager_timer.cancel()
        if skill_reload_thread:
            skill_reload_thread.stop()
            skill_reload_thread.join()

    finally:
        sys.exit()
