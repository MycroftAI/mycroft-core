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


TIMEOUT = 10


def then_wait(msg_type, criteria_func, context, timeout=TIMEOUT):
    """Wait for a specified time for criteria to be fulfilled.

    Arguments:
        msg_type: message type to watch
        criteria_func: Function to determine if a message fulfilling the
                       test case has been found.
        context: behave context
        timeout: Time allowance for a message fulfilling the criteria

    Returns:
        tuple (bool, str) test status and debug output
    """
    start_time = time.monotonic()
    debug = ''
    while time.monotonic() < start_time + timeout:
        for message in context.bus.get_messages(msg_type):
            status, test_dbg = criteria_func(message)
            debug += test_dbg
            if status:
                context.matched_message = message
                context.bus.remove_message(message)
                return True, debug
        context.bus.new_message_available.wait(0.5)
    # Timed out return debug from test
    return False, debug


def mycroft_responses(context):
    """Collect and format mycroft responses from context.

    Arguments:
        context: behave context to extract messages from.

    Returns: (str) Mycroft responses including skill and dialog file
    """
    responses = ''
    messages = context.bus.get_messages('speak')
    if len(messages) > 0:
        responses = 'Mycroft responded with:\n'
        for m in messages:
            responses += 'Mycroft: '
            if 'dialog' in m.data['meta']:
                responses += '{}.dialog'.format(m.data['meta']['dialog'])
            responses += '({})\n'.format(m.data['meta'].get('skill'))
            responses += '"{}"\n'.format(m.data['utterance'])
    return responses


def print_mycroft_responses(context):
    print(mycroft_responses(context))


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
    start_time = time.monotonic()
    while time.monotonic() < start_time + timeout:
        for message in bus.get_messages('speak'):
            dialog = message.data.get('meta', {}).get('dialog')
            if dialog in dialogs:
                bus.clear_messages()
                return
        bus.new_message_available.wait(0.5)
    bus.clear_messages()
