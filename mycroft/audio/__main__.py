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
"""Mycroft audio service.

    This handles playback of audio and speech
"""
from mycroft.configuration import Configuration
from mycroft.messagebus.client import MessageBusClient
from mycroft.util import reset_sigint_handler, wait_for_exit_signal, \
    create_daemon, create_echo_function, check_for_signal
from mycroft.util.log import LOG

import mycroft.audio.speech as speech
from .audioservice import AudioService


def on_ready():
    LOG.info('Audio service is ready.')


def on_error(e='Unknown'):
    LOG.error('Audio service failed to launch ({}).'.format(repr(e)))


def on_stopping():
    LOG.info('Audio service is shutting down...')


def main(ready_hook=on_ready, error_hook=on_error, stopping_hook=on_stopping):
    """ Main function. Run when file is invoked. """
    try:
        reset_sigint_handler()
        check_for_signal("isSpeaking")
        bus = MessageBusClient()  # Connect to the Mycroft Messagebus
        Configuration.set_config_update_handlers(bus)
        speech.init(bus)

        LOG.info("Starting Audio Services")
        bus.on('message', create_echo_function('AUDIO',
                                               ['mycroft.audio.service']))

        # Connect audio service instance to message bus
        audio = AudioService(bus)
    except Exception as e:
        error_hook(e)
    else:
        create_daemon(bus.run_forever)
        if audio.wait_for_load() and len(audio.service) > 0:
            # If at least one service exists, report ready
            ready_hook()
            wait_for_exit_signal()
            stopping_hook()
        else:
            error_hook('No audio services loaded')

        speech.shutdown()
        audio.shutdown()


if __name__ == '__main__':
    main()
