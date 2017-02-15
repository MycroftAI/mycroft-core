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
from os.path import expanduser, exists

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.skills.core import load_skills, THIRD_PARTY_SKILLS_DIR
from mycroft.util.log import getLogger

logger = getLogger("Skills")

__author__ = 'seanfitz'

ws = None
skills = []


def load_skills_callback():
    global ws
    global skills
    skills += load_skills(ws)
    config = ConfigurationManager.get().get("skills")

    try:
        ini_third_party_skills_dir = expanduser(config.get("directory"))
    except AttributeError as e:
        logger.warning(e.message)

    for loc in THIRD_PARTY_SKILLS_DIR:
        if exists(loc):
            skills += load_skills(ws, loc)

    if ini_third_party_skills_dir and exists(ini_third_party_skills_dir):
        skills += load_skills(ws, ini_third_party_skills_dir)


def connect():
    global ws
    ws.run_forever()


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
    ws.once('open', load_skills_callback)
    ws.run_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        for skill in skills:
            skill.shutdown()
    finally:
        sys.exit()
