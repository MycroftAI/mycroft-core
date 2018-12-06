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
import sys

from mycroft.util.log import LOG
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.configuration import Configuration, LocalConf, SYSTEM_CONFIG


def main():
    # Read the system configuration
    system_config = LocalConf(SYSTEM_CONFIG)
    platform = system_config.get("enclosure", {}).get("platform")

    if platform == "mycroft_mark_1":
        LOG.debug("Creating Mark I Enclosure")
        from mycroft.client.enclosure.mark1 import EnclosureMark1
        enclosure = EnclosureMark1()
    elif platform == "mycroft_mark_2":
        LOG.debug("Creating Mark II Enclosure")
        from mycroft.client.enclosure.mark2 import EnclosureMark2
        enclosure = EnclosureMark2()
    else:
        LOG.debug("Creating generic enclosure, platform='{}'".format(platform))

        # TODO: Mechanism to load from elsewhere.  E.g. read a script path from
        # the mycroft.conf, then load/launch that script.
        from mycroft.client.enclosure.generic import EnclosureGeneric
        enclosure = EnclosureGeneric()

    if enclosure:
        try:
            LOG.debug("Enclosure started!")
            enclosure.run()
        except Exception as e:
            print(e)
        finally:
            sys.exit()
    else:
        LOG.debug("No enclosure available for this hardware, running headless")


if __name__ == "__main__":
    main()
