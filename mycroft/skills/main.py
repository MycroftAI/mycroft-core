# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import json
import os
import subprocess
import sys
import time
from os.path import exists, join
from threading import Timer

from mycroft import MYCROFT_ROOT_PATH
from mycroft.configuration import ConfigurationManager
from mycroft.lock import Lock  # Creates PID file for single instance
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.skills.core import load_skill, create_skill_descriptor, \
    MainModule, SKILLS_DIR
from mycroft.skills.intent_service import IntentService
from mycroft.util import connected
from mycroft.util.log import getLogger
from mycroft.api import is_paired
import mycroft.dialog

logger = getLogger("Skills")

__author__ = 'seanfitz'

ws = None
loaded_skills = {}
last_modified_skill = 0
skills_directories = []
skill_reload_thread = None
skills_manager_timer = None

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
            logger.error('msm failed, network connection is not available')
            ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("no network connection")}))
        elif res != 0:
            logger.error('msm failed with error {}: {}'.format(res, output))
            ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get(
                             "sorry I couldn't install default skills")}))

    else:
        logger.error("Unable to invoke Mycroft Skill Manager: " + MSM_BIN)


def skills_manager(message):
    global skills_manager_timer, ws

    if connected():
        if skills_manager_timer is None:
            pass
            # ws.emit(
            #     Message("speak", {'utterance':
            #             mycroft.dialog.get("checking for updates")}))

        # Install default skills and look for updates via Github
        logger.debug("==== Invoking Mycroft Skill Manager: " + MSM_BIN)
        install_default_skills(False)

    # Perform check again once and hour
    skills_manager_timer = Timer(3600, _skills_manager_dispatch)
    skills_manager_timer.daemon = True
    skills_manager_timer.start()


def _skills_manager_dispatch():
    ws.emit(Message("skill_manager", {}))


def _load_skills():
    global ws, loaded_skills, last_modified_skill, skills_directories, \
        skill_reload_thread

    check_connection()

    # Create skill_manager listener and invoke the first time
    ws.on('skill_manager', skills_manager)
    ws.on('mycroft.internet.connected', install_default_skills)
    ws.emit(Message('skill_manager', {}))

    # Create the Intent manager, which converts utterances to intents
    # This is the heart of the voice invoked skill system
    IntentService(ws)

    # Create a thread that monitors the loaded skills, looking for updates
    skill_reload_thread = Timer(0, _watch_skills)
    skill_reload_thread.daemon = True
    skill_reload_thread.start()


def check_connection():
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
    last_date = 0
    # getting all recursive paths
    for root, _, _ in os.walk(path):
        f = root.replace(path, "")
        # checking if is a hidden path
        if not f.startswith(".") and not f.startswith("/."):
            last_date = max(last_date, os.path.getmtime(path + f))

    return last_date


def _watch_skills():
    global ws, loaded_skills, last_modified_skill, \
        id_counter

    # Scan the file folder that contains Skills.  If a Skill is updated,
    # unload the existing version from memory and reload from the disk.
    while True:
        if exists(SKILLS_DIR):
            # checking skills dir and getting all skills there
            list = filter(lambda x: os.path.isdir(
                os.path.join(SKILLS_DIR, x)), os.listdir(SKILLS_DIR))

            for skill_folder in list:
                if skill_folder not in loaded_skills:
                    loaded_skills[skill_folder] = {}
                skill = loaded_skills.get(skill_folder)
                skill["path"] = os.path.join(SKILLS_DIR, skill_folder)
                # checking if is a skill
                if not MainModule + ".py" in os.listdir(skill["path"]):
                    continue
                # getting the newest modified date of skill
                skill["last_modified"] = _get_last_modified_date(skill["path"])
                modified = skill.get("last_modified", 0)
                # checking if skill is loaded and wasn't modified
                if skill.get(
                        "loaded") and modified <= last_modified_skill:
                    continue
                # checking if skill was modified
                elif skill.get(
                        "instance") and modified > last_modified_skill:
                    # checking if skill should be reloaded
                    if not skill["instance"].reload_skill:
                        continue
                    logger.debug("Reloading Skill: " + skill_folder)
                    # removing listeners and stopping threads
                    skill["instance"].shutdown()
                    del skill["instance"]
                skill["loaded"] = True
                skill["instance"] = load_skill(
                    create_skill_descriptor(skill["path"]), ws)
        # get the last modified skill
        modified_dates = map(lambda x: x.get("last_modified"),
                             loaded_skills.values())
        if len(modified_dates) > 0:
            last_modified_skill = max(modified_dates)

        # Pause briefly before beginning next scan
        time.sleep(2)


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
        logger.debug(message)

    ws.on('message', _echo)

    # Kick off loading of skills
    ws.once('open', _load_skills)
    ws.run_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        skills_manager_timer.cancel()
        for skill in loaded_skills:
            skill.shutdown()
        if skill_reload_thread:
            skill_reload_thread.cancel()

    finally:
        sys.exit()
