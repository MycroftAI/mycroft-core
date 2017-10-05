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
import time

import psutil

from mycroft.util.signal import check_for_signal


def is_speaking():
    """Determine if Text to Speech is occurring

    Returns:
        bool: True while still speaking
    """
    return check_for_signal("isSpeaking", -1)


def wait_while_speaking():
    """Pause as long as Text to Speech is still happening

    Pause while Text to Speech is still happening.  This always pauses
    briefly to ensure that any preceeding request to speak has time to
    begin.
    """
    time.sleep(0.1)  # Wait briefly in for any queued speech to begin
    while is_speaking():
        time.sleep(0.1)


def _kill(names):
    print psutil.pids()
    for name in names:
        for p in psutil.process_iter():
            try:
                if p.name() == name:
                    p.kill()
                    break
            except:
                pass


def stop_speaking():
    # TODO: Less hacky approach to this once Audio Manager is implemented
    # Skills should only be able to stop speech they've initiated
    config = mycroft.configuration.ConfigurationManager.instance()

    create_signal('stoppingTTS')

    # Perform in while loop in case the utterance contained periods and was
    # split into multiple chunks by handle_speak()
    while check_for_signal("isSpeaking", -1):
        _kill([config.get('tts').get('module')])
        _kill(["aplay"])
        time.sleep(0.25)

    # This consumes the signal
    check_for_signal('stoppingTTS')
