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
import sys
import time
from threading import Timer

import os
from os.path import expanduser, exists

from mycroft.messagebus.message import Message
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.skills.core import load_skills, THIRD_PARTY_SKILLS_DIR, \
    load_skill, create_skill_descriptor, MainModule
from mycroft.util.log import getLogger

logger = getLogger("Skills")

__author__ = 'seanfitz'

ws = None
loaded_skills = {}
last_modified_skill = 0
skills_directories = []
skill_reload_thread = None
id_counter = 0

def connect():
    global ws
    ws.run_forever()


def load_watch_skills():
    global ws, loaded_skills, last_modified_skill, skills_directories, \
        skill_reload_thread

    skills_directories = [os.path.dirname(os.path.abspath(__file__))]
    skills_directories = skills_directories + THIRD_PARTY_SKILLS_DIR

    try:
        config = ConfigurationManager.get().get("skills")
        ini_third_party_skills_dir = expanduser(config.get("directory"))
        if ini_third_party_skills_dir and exists(ini_third_party_skills_dir):
            skills_directories.append(ini_third_party_skills_dir)
    except AttributeError as e:
        logger.warning(e.message)

    skill_reload_thread = Timer(0, watch_skills)
    skill_reload_thread.daemon = True
    skill_reload_thread.start()


def clear_skill_events(instance):
    global ws
    events = ws.emitter._events
    instance_events = []
    for event in events:
        e = ws.emitter._events[event]
        if len(e) > 0 and e[0].func_closure and isinstance(
                e[0].func_closure[1].cell_contents, instance.__class__):
            instance_events.append(event)

    for event in instance_events:
        del events[event]


def watch_skills():
    global ws, loaded_skills, last_modified_skill, skills_directories
    while True:
        for dir in skills_directories:
            if exists(dir):
                list = filter(lambda x: os.path.isdir(os.path.join(dir, x)),
                              os.listdir(dir))
                for skill_folder in list:
                    if skill_folder not in loaded_skills:
                        ####### register unique ID
                        global id_counter
                        id_counter += 1
                        loaded_skills[skill_folder] = {"id":id_counter}
                    skill = loaded_skills.get(skill_folder)
                    skill["path"] = os.path.join(dir, skill_folder)
                    if not MainModule + ".py" in os.listdir(skill["path"]):
                        continue
                    skill["last_modified"] = max(
                        os.path.getmtime(root) for root, _, _ in
                        os.walk(skill["path"]))
                    modified = skill.get("last_modified", 0)
                    if skill.get(
                            "loaded") and modified <= last_modified_skill:
                        continue
                    elif skill.get(
                            "instance") and modified > last_modified_skill:
                        #### this would break stuff during testing always trigger wolphram alpha on intent reload
                        if skill_folder == "intent":
                            continue
                        #####
                        logger.debug("Reloading Skill: " + skill_folder)
                        skill["instance"].shutdown()
                        clear_skill_events(skill["instance"])
                        del skill["instance"]
                    skill["loaded"] = True
                    skill["instance"] = load_skill(
                        create_skill_descriptor(skill["path"]), ws, skill["id"])


        last_modified_skill = max(
            map(lambda x: x.get("last_modified"), loaded_skills.values()))
        time.sleep(2)


def handle_conversation_request(message):
    skill_id = message.data["skill_id"]
    utterances = message.data["utterances"]
    global ws, loaded_skills
    # loop trough skills list and call converse for skill with skill_id
    for skill in loaded_skills:
        if loaded_skills[skill]["id"] == skill_id:
            instance = loaded_skills[skill]["instance"]
            result = instance.Converse(utterances)
            ws.emit(Message("converse_status_response", {"skill_id": skill_id, "result": result}))
            return



def main():
    global ws
    ws = WebsocketClient()
    ConfigurationManager.init(ws)

    def echo(message):
        try:
            _message = json.loads(message)

            if _message.get("type") == "registration":
                # do not log tokens from registration messages
                _message["data"]["token"] = None
            message = json.dumps(_message)
        except:
            pass
        logger.debug(message)

    ws.on('message', echo)
    ws.once('open', load_watch_skills)
    ws.on('converse_status_request', handle_conversation_request)
    ws.run_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        for skill in loaded_skills:
            skill.shutdown()
        if skill_reload_thread:
            skill_reload_thread.cancel()

    finally:
        sys.exit()
