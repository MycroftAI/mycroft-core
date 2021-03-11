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


def then_wait(msg_type, criteria_func, context, timeout=None):
    """Wait for a specified time for criteria to be fulfilled.

    Arguments:
        msg_type: message type to watch
        criteria_func: Function to determine if a message fulfilling the
                       test case has been found.
        context: behave context
        timeout: Time allowance for a message fulfilling the criteria, if
                 provided will override the normal normal step timeout.

    Returns:
        tuple (bool, str) test status and debug output
    """
    timeout = timeout or context.step_timeout
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


def then_wait_fail(msg_type, criteria_func, context, timeout=None):
    """Wait for a specified time, failing if criteria is fulfilled.

    Arguments:
        msg_type: message type to watch
        criteria_func: Function to determine if a message fulfilling the
                       test case has been found.
        context: behave context
        timeout: Time allowance for a message fulfilling the criteria

    Returns:
        tuple (bool, str) test status and debug output
    """
    status, debug = then_wait(msg_type, criteria_func, context, timeout)
    return (not status, debug)


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
            if 'meta' in m.data and 'dialog' in m.data['meta']:
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


def wait_for_dialog(bus, dialogs, context=None, timeout=None):
    """Wait for one of the dialogs given as argument.

    Arguments:
        bus (InterceptAllBusClient): Bus instance to listen on
        dialogs (list): list of acceptable dialogs
        context (behave Context): optional context providing scenario timeout
        timeout (int): how long to wait for the message, defaults to timeout
                       provided by context or 10 seconds
    """
    if context:
        timeout = timeout or context.step_timeout
    else:
        timeout = timeout or TIMEOUT
    start_time = time.monotonic()
    while time.monotonic() < start_time + timeout:
        for message in bus.get_messages('speak'):
            dialog = message.data.get('meta', {}).get('dialog')
            if dialog in dialogs:
                bus.clear_messages()
                return
        bus.new_message_available.wait(0.5)
    bus.clear_messages()


def wait_for_audio_service(context, message_type):
    """Wait for audio.service message that matches type provided.

    May be play, stop, or pause messages

    Arguments:
        context (behave Context): optional context providing scenario timeout
        message_type (string): final component of bus message in form
                               `mycroft.audio.service.{type}
    """
    msg_type = 'mycroft.audio.service.{}'.format(message_type)

    def check_for_msg(message):
        return (message.msg_type == msg_type, '')

    passed, debug = then_wait(msg_type, check_for_msg, context)

    if not passed:
        debug += mycroft_responses(context)
    if not debug:
        if message_type == 'play':
            message_type = 'start'
        debug = "Mycroft didn't {} playback".format(message_type)

    assert passed, debug
