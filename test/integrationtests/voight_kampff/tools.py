# Copyright 2020 Mycroft AI Inc.
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

"""Common tools to use when creating step files for behave tests."""

import time

from mycroft.messagebus import Message


SLEEP_LENGTH = 0.25
TIMEOUT = 10


def emit_utterance(bus, utt):
    """Emit an utterance on the bus.

    Arguments:
        bus (InterceptAllBusClient): Bus instance to listen on
        dialogs (list): list of acceptable dialogs
    """
    bus.emit(Message('recognizer_loop:utterance',
                     data={'utterances': [utt],
                           'lang': 'en-us',
                           'session': '',
                           'ident': time.time()},
                     context={'client_name': 'mycroft_listener'}))


def wait_for_dialog(bus, dialogs, timeout=TIMEOUT):
    """Wait for one of the dialogs given as argument.

    Arguments:
        bus (InterceptAllBusClient): Bus instance to listen on
        dialogs (list): list of acceptable dialogs
        timeout (int): how long to wait for the messagem, defaults to 10 sec.
    """
    for t in range(int(timeout * (1 / SLEEP_LENGTH))):
        for message in bus.get_messages('speak'):
            dialog = message.data.get('meta', {}).get('dialog')
            if dialog in dialogs:
                bus.clear_messages()
                return
        time.sleep(SLEEP_LENGTH)
    bus.clear_messages()
