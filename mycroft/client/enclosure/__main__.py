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
from mycroft.configuration import Configuration
from mycroft.util.log import LOG
from mycroft.util import wait_for_exit_signal, reset_sigint_handler
from mycroft.util.hardware_capabilities import EnclosureCapabilities


def on_ready():
    LOG.info("Enclosure service is ready")


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
        LOG.info("Initializing Mark I enclosure...")
        from mycroft.client.enclosure.mark1 import EnclosureMark1
        enclosure = EnclosureMark1()
    elif platform == "mycroft_mark_2":
        LOG.info("Initializing Mark II enclosure...")
        from mycroft.client.enclosure.mark2 import EnclosureMark2
        enclosure = EnclosureMark2()
    else:
        LOG.info(f"Initializing generic enclosure, platform='{platform}'")
        # TODO: Mechanism to load from elsewhere.  E.g. read a script path from
        # the mycroft.conf, then load/launch that script.
        from mycroft.client.enclosure.generic import EnclosureGeneric
        enclosure = EnclosureGeneric()

    LOG.info("Enclosure initialized")

    return enclosure


def main(ready_hook=on_ready, error_hook=on_error, stopping_hook=on_stopping):
    """Launch one of the available enclosure implementations.

    This depends on the configured platform and can currently either be
    mycroft_mark_1 or mycroft_mark_2, if unconfigured a generic enclosure with
    only the GUI bus will be started.
    """
    LOG.info("Starting Enclosure Service")
    config = Configuration.get(remote=False)
    platform = config.get("enclosure", {}).get("platform")
    enclosure = create_enclosure(platform)

    # crude attempt to deal with hardware beyond custom hat
    # note - if using a Mark2 you will also have
    # enclosure.m2enc.capabilities
    enclosure.default_caps = EnclosureCapabilities()
    LOG.info(f"Enclosure capabilities ===> {enclosure.default_caps.caps}")
    if platform == "mycroft_mark_2":
        LOG.info(f"Mark II detected [{enclosure.hardware.board_type}]\n"
                 f"additional capabilities ===> "
                 f"{enclosure.hardware.capabilities}\n"
                 f"LEDs ===> {enclosure.hardware.leds.capabilities}\n"
                 f"Volume ===> "
                 f"{enclosure.hardware.hardware_volume.capabilities}\n"
                 f"Switches ===> "
                 f"{enclosure.hardware.switches.capabilities}")

    try:
        reset_sigint_handler()
        enclosure.run()
        ready_hook()
        wait_for_exit_signal()
        enclosure.stop()
        stopping_hook()
    except Exception as e:
        error_hook(e)


if __name__ == "__main__":
    main()
