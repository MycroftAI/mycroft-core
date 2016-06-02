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


import sys
import os
import argparse
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.skills.core import create_skill_descriptor, load_skill
from mycroft.util.log import getLogger
from mycroft.configuration.config import ConfigurationManager
from mycroft.configuration.config import ConfigBuilder
from mycroft.skills.intent import create_skill as create_intent_skill

__author__ = 'seanfitz'

logger = getLogger("SkillContainer")
messagebus_config = ConfigurationManager.get_config().get("messagebus_client")


class SkillContainer(object):
    def __init__(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--dependency-dir", default="./lib")
        parser.add_argument("--default-config", default="./config/mycroft.ini")
        parser.add_argument(
            "--messagebus-host", default=messagebus_config.get("host"))
        parser.add_argument(
            "--messagebus-port", type=int,
            default=messagebus_config.get("port"))
        parser.add_argument("--use-ssl", action='store_true', default=False)
        parser.add_argument(
            "--enable-intent-skill", action='store_true', default=False)
        parser.add_argument(
            "skill_directory", default=os.path.dirname(__file__))

        parsed_args = parser.parse_args(args)
        if os.path.exists(parsed_args.default_config):
            configs = ConfigBuilder() \
                .base() \
                .with_default(parsed_args.default_config)
            ConfigurationManager.load(configs)

        if os.path.exists(parsed_args.dependency_dir):
            sys.path.append(parsed_args.dependency_dir)
        sys.path.append(parsed_args.skill_directory)

        self.skill_directory = parsed_args.skill_directory

        self.enable_intent_skill = parsed_args.enable_intent_skill

        self.client = WebsocketClient(host=parsed_args.messagebus_host,
                                      port=parsed_args.messagebus_port,
                                      ssl=parsed_args.use_ssl)

    def try_load_skill(self):
        if self.enable_intent_skill:
            intent_skill = create_intent_skill()
            intent_skill.bind(self.client)
            intent_skill.initialize()
        skill_descriptor = create_skill_descriptor(self.skill_directory)
        load_skill(skill_descriptor, self.client)

    def run(self):
        self.client.on('message', logger.debug)
        self.client.on('open', self.try_load_skill)
        self.client.on('error', logger.error)
        self.client.run_forever()


def main():
    SkillContainer(sys.argv[1:]).run()


if __name__ == "__main__":
    main()
