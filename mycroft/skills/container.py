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


import argparse
import sys
from os.path import dirname, exists, isdir

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.skills.core import create_skill_descriptor, load_skill
from mycroft.skills.intent_service import IntentService
from mycroft.util.log import getLogger

__author__ = 'seanfitz'

LOG = getLogger("SkillContainer")


class SkillContainer(object):
    def __init__(self, args):
        params = self.__build_params(args)

        if params.config:
            ConfigurationManager.load_local([params.config])

        if exists(params.lib) and isdir(params.lib):
            sys.path.append(params.lib)

        sys.path.append(params.dir)
        self.dir = params.dir

        self.enable_intent = params.enable_intent

        self.__init_client(params)

    @staticmethod
    def __build_params(args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", default="./mycroft.conf")
        parser.add_argument("dir", nargs='?', default=dirname(__file__))
        parser.add_argument("--lib", default="./lib")
        parser.add_argument("--host", default=None)
        parser.add_argument("--port", default=None)
        parser.add_argument("--use-ssl", action='store_true', default=False)
        parser.add_argument("--enable-intent", action='store_true',
                            default=False)
        return parser.parse_args(args)

    def __init_client(self, params):
        config = ConfigurationManager.get().get("websocket")

        if not params.host:
            params.host = config.get('host')
        if not params.port:
            params.port = config.get('port')

        self.ws = WebsocketClient(host=params.host,
                                  port=params.port,
                                  ssl=params.use_ssl)

        # Connect configuration manager to message bus to receive updates
        ConfigurationManager.init(self.ws)

    def load_skill(self):
        if self.enable_intent:
            IntentService(self.ws)

        skill_descriptor = create_skill_descriptor(self.dir)
        self.skill = load_skill(skill_descriptor, self.ws, hash(self.dir))

    def run(self):
        try:
            self.ws.on('message', LOG.debug)
            self.ws.on('open', self.load_skill)
            self.ws.on('error', LOG.error)
            self.ws.run_forever()
        except Exception as e:
            LOG.error("Error: {0}".format(e))
            self.stop()

    def stop(self):
        if self.skill:
            self.skill.shutdown()


def main():
    container = SkillContainer(sys.argv[1:])
    try:
        container.run()
    except KeyboardInterrupt:
        container.stop()
    finally:
        sys.exit()


if __name__ == "__main__":
    main()
