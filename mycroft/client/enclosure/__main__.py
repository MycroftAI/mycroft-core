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
"""Entrypoint for enclosure service.

This provides any "enclosure" specific functionality, for example GUI or
control over the Mark-1 Faceplate.
"""
from mycroft.configuration import setup_locale
from mycroft.configuration import Configuration
from mycroft.util.log import LOG
from mycroft.util import wait_for_exit_signal, reset_sigint_handler


def on_ready():
    LOG.info("Enclosure started!")


def on_stopping():
    LOG.info('Enclosure is shutting down...')


def on_error(e='Unknown'):
    LOG.error('Enclosure failed: {}'.format(repr(e)))


def create_enclosure(platform):
    """Create an enclosure based on the provided platform string.

    Args:
        platform (str): platform name string

    Returns:
        Enclosure object
    """
    if platform == "mycroft_mark_1":
        LOG.info("Creating Mark I Enclosure")
        from mycroft.client.enclosure.mark1 import EnclosureMark1
        enclosure = EnclosureMark1()
    elif platform == "mycroft_mark_2":
        LOG.info("Creating Mark II Enclosure")
        from mycroft.client.enclosure.mark2 import EnclosureMark2
        enclosure = EnclosureMark2()
    else:
        LOG.info("Creating generic enclosure, platform='{}'".format(platform))
        from mycroft.client.enclosure.generic import EnclosureGeneric
        enclosure = EnclosureGeneric()

    return enclosure


def main(ready_hook=on_ready, error_hook=on_error, stopping_hook=on_stopping):
    """Launch one of the available enclosure implementations.

    This depends on the configured platform and can currently either be
    mycroft_mark_1 or mycroft_mark_2, if unconfigured a generic enclosure will be started.

    NOTE: in ovos-core the GUI protocol is handled in it's own service and not part of the enclosure like in mycroft-core!
          You need to also run mycroft.gui process separately, it has been extracted into it's own module
    """
    LOG.warning("mycroft.client.enclosure is in the process of being deprecated in ovos-core!")
    LOG.warning("You need to also run mycroft.gui process separately, it has been extracted into it's own module")

    # Read the system configuration
    config = Configuration.get(remote=False)
    platform = config.get("enclosure", {}).get("platform")

    enclosure = create_enclosure(platform)
    if enclosure:
        LOG.debug("Enclosure created")
        try:
            reset_sigint_handler()
            setup_locale()
            enclosure.run()
            ready_hook()
            wait_for_exit_signal()
            enclosure.stop()
            stopping_hook()
        except Exception as e:
            error_hook(e)
    else:
        LOG.info("No enclosure available for this hardware, running headless")


if __name__ == "__main__":
    main()
