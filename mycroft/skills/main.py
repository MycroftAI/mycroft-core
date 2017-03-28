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
prioritary_skills = ["intent"]


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
        if len(e) == 0:
            continue
        if getattr(e[0], 'func_closure', None) is not None and isinstance(
                e[0].func_closure[1].cell_contents, instance.__class__):
            instance_events.append(event)
        elif getattr(e[0], 'im_class', None) is not None and e[0].\
                im_class == instance.__class__:
            instance_events.append(event)
        elif getattr(e[0], 'im_self', None) is not None and isinstance(
                e[0].im_self, instance.__class__):
            instance_events.append(event)

    for event in instance_events:
        del events[event]


def watch_skills():
    global ws, loaded_skills, last_modified_skill, skills_directories, \
        id_counter, prioritary_skills
    # load prioritary skills first
    for p_skill in prioritary_skills:
        if p_skill not in loaded_skills:
            loaded_skills[p_skill] = {}
            skill = loaded_skills.get(p_skill)
            skill["path"] = os.path.join(os.path.dirname(__file__), p_skill)
            if not MainModule + ".py" in os.listdir(skill["path"]):
                logger.error(p_skill + " does not appear to be a skill")
                sys.exit(1)
            skill["loaded"] = True
            skill["instance"] = load_skill(
                create_skill_descriptor(skill["path"]), ws)

    while True:
        for dir in skills_directories:
            if exists(dir):
                list = sorted(
                    filter(lambda x: os.path.isdir(os.path.join(dir, x)),
                           os.listdir(dir)))
                for skill_folder in list:
                    if skill_folder not in loaded_skills:
                        loaded_skills[skill_folder] = {}
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
                        if not skill["instance"].reload_skill:
                            continue
                        logger.debug("Reloading Skill: " + skill_folder)
                        skill["instance"].shutdown()
                        clear_skill_events(skill["instance"])
                        del skill["instance"]
                    skill["loaded"] = True
                    skill["instance"] = load_skill(
                        create_skill_descriptor(skill["path"]), ws)
        last_modified_skill = max(
            map(lambda x: x.get("last_modified"), loaded_skills.values()))
        time.sleep(2)


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
