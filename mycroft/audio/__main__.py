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
from mycroft.messagebus import Message
from mycroft.util import (
    check_for_signal,
    reset_sigint_handler,
    start_message_bus_client,
    wait_for_exit_signal
)
from mycroft.util.log import LOG
from mycroft.util.process_utils import ProcessStatus, StatusCallbackMap

import mycroft.audio.speech as speech

from .audio_ui import AudioUserInterface

def on_ready():
    LOG.info('Audio service is ready.')


def on_error(e='Unknown'):
    LOG.error('Audio service failed to launch ({}).'.format(repr(e)))


def on_stopping():
    LOG.info('Audio service is shutting down...')


def main(ready_hook=on_ready, error_hook=on_error, stopping_hook=on_stopping):
    """Start the Audio Service and connect to the Message Bus"""
    LOG.info("Starting Audio Service")
    reset_sigint_handler()
    check_for_signal("isSpeaking")
    whitelist = ['mycroft.audio.service']
    bus = start_message_bus_client("AUDIO", whitelist=whitelist)
    bus.emit(Message("audio.initialize.started"))
    callbacks = StatusCallbackMap(on_ready=ready_hook, on_error=error_hook,
                                  on_stopping=stopping_hook, on_alive=None)
    status = ProcessStatus('audio', bus, callbacks)
    status.set_started()
    try:
        aui = AudioUserInterface()
        aui.initialize(bus)

        speech.init(bus)
    except Exception as e:
        LOG.exception("loading audio service")
        status.set_error(e)
    else:
        status.set_ready()
        wait_for_exit_signal()
        status.set_stopping()

        speech.shutdown()
        aui.shutdown()


if __name__ == '__main__':
    main()
