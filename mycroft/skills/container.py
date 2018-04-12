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
import argparse
import sys

from os.path import dirname, exists, isdir

from mycroft.configuration import Configuration
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.skills.core import create_skill_descriptor, load_skill
from mycroft.skills.intent_service import IntentService
from mycroft.util.log import LOG


class SkillContainer(object):
    def __init__(self, args):
        params = self.__build_params(args)

        if params.config:
            Configuration.get([params.config])

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
        config = Configuration.get().get("websocket")

        if not params.host:
            params.host = config.get('host')
        if not params.port:
            params.port = config.get('port')

        self.ws = WebsocketClient(host=params.host,
                                  port=params.port,
                                  ssl=params.use_ssl)

        # Connect configuration manager to message bus to receive updates
        Configuration.init(self.ws)

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
            self.skill._shutdown()


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
