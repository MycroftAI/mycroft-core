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

from threading import Event
import time

from mycroft.audio.utils import wait_while_speaking
from mycroft.messagebus import Message


DEFAULT_TIMEOUT = 10


class CriteriaWaiter:
    """Wait for a message to meet a certain criteria.

    Args:
        msg_type: message type to watch
        criteria_func: Function to determine if a message fulfilling the
                    test case has been found.
        context: behave context
    """
    def __init__(self, msg_type, criteria_func, context):
        self.msg_type = msg_type
        self.criteria_func = criteria_func
        self.context = context
        self.result = Event()

    def reset(self):
        """Reset the wait state."""
        self.result.clear()

    # TODO: Remove in 21.08
    def wait_unspecific(self, timeout):
        """
        Wait for a specified time for criteria to be fulfilled by any message.

        This use case is deprecated and only for backward compatibility

        Args:
            timeout: Time allowance for a message fulfilling the criteria, if
                    provided will override the normal normal step timeout.

        Returns:
            tuple (bool, str) test status and debug output
        """
        timeout = timeout or self.context.step_timeout
        start_time = time.monotonic()
        debug = ''
        while time.monotonic() < start_time + timeout:
            for message in self.context.bus.get_messages(None):
                status, test_dbg = self.criteria_func(message)
                debug += test_dbg
                if status:
                    self.context.matched_message = message
                    self.context.bus.remove_message(message)
                    return True, debug
            self.context.bus.new_message_available.wait(0.5)
        # Timed out return debug from test
        return False, debug

    def _check_historical_messages(self):
        """Search through the already received messages for a match.

        Returns:
            tuple (bool, str) test status and debug output

        """
        debug = ''
        for message in self.context.bus.get_messages(self.msg_type):
            status, test_dbg = self.criteria_func(message)
            debug += test_dbg
            if status:
                self.context.matched_message = message
                self.context.bus.remove_message(message)
                self.result.set()
                break
        return debug

    def wait_specific(self, timeout=None):
        """Wait for a specific message type to fullfil a criteria.

        Uses an event-handler to not repeatedly loop.

        Args:
            timeout: Time allowance for a message fulfilling the criteria, if
                    provided will override the normal normal step timeout.

        Returns:
            tuple (bool, str) test status and debug output
        """
        timeout = timeout or self.context.step_timeout

        debug = ''

        def on_message(message):
            nonlocal debug
            status, test_dbg = self.criteria_func(message)
            debug += test_dbg
            if status:
                self.context.matched_message = message
                self.result.set()

        self.context.bus.on(self.msg_type, on_message)
        # Check historical messages
        historical_debug = self._check_historical_messages()

        # If no matching message was already caught, wait for it
        if not self.result.is_set():
            self.result.wait(timeout=timeout)
        self.context.bus.remove(self.msg_type, on_message)
        return self.result.is_set(), historical_debug + debug

    def wait(self, timeout=None):
        """Wait for a specific message type to fullfil a criteria.

        Uses an event-handler to not repeatedly loop.

        Args:
            timeout: Time allowance for a message fulfilling the criteria, if
                    provided will override the normal normal step timeout.

        Returns:
            (result (bool), debug (str)) Result containing status and debug
            message.
        """
        if self.msg_type is None:
            return self.wait_unspecific(timeout)
        else:
            return self.wait_specific(timeout)


def then_wait(msg_type, criteria_func, context, timeout=None):
    """Wait for a specific message type to fullfil a criteria.

    Uses an event-handler to not repeatedly loop.

    Args:
        msg_type: message type to watch
        criteria_func: Function to determine if a message fulfilling the
                       test case has been found.
        context: behave context
        timeout: Time allowance for a message fulfilling the criteria, if
                 provided will override the normal normal step timeout.

    Returns:
        (result (bool), debug (str)) Result containing status and debug
        message.
    """
    waiter = CriteriaWaiter(msg_type, criteria_func, context)
    return waiter.wait(timeout)


def then_wait_fail(msg_type, criteria_func, context, timeout=None):
    """Wait for a specified time, failing if criteria is fulfilled.

    Args:
        msg_type: message type to watch
        criteria_func: Function to determine if a message fulfilling the
                       test case has been found.
        context: behave context
        timeout: Time allowance for a message fulfilling the criteria

    Returns:
        tuple (bool, str) test status and debug output
    """
    status, debug = then_wait(msg_type, criteria_func, context, timeout)
    return not status, debug


def mycroft_responses(context):
    """Collect and format mycroft responses from context.

    Args:
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


def format_dialog_match_error(potential_matches, speak_messages):
    """Format error message to be displayed when an expected

    This is similar to the mycroft_responses function above.  The difference
    is that here the expected responses are passed in instead of making
    a second loop through message bus messages.

    Args:
        potential_matches (list): one of the dialog files in this list were
            expected to be spoken
        speak_messages (list): "speak" event messages from the message bus
            that don't match the list of potential matches.

    Returns: (str) Message detailing the error to the user
    """
    error_message = (
        'Expected Mycroft to respond with one of:\n'
        f"\t{', '.join(potential_matches)}\n"
        "Actual response(s):\n"
    )
    if speak_messages:
        for message in speak_messages:
            meta = message.data.get("meta")
            if meta is not None:
                if 'dialog' in meta:
                    error_message += f"\tDialog: {meta['dialog']}"
                if 'skill' in meta:
                    error_message += f" (from {meta['skill']} skill)\n"
            error_message += f"\t\tUtterance: {message.data['utterance']}\n"
    else:
        error_message += "\tMycroft didn't respond"

    return error_message


def emit_utterance(bus, utterance):
    """Emit an utterance event on the message bus.

    Args:
        bus (InterceptAllBusClient): Bus instance to listen on
        utterance (str): list of acceptable dialogs
    """
    bus.emit(Message('recognizer_loop:utterance',
                     data={'utterances': [utterance],
                           'lang': 'en-us',
                           'session': '',
                           'ident': time.time()},
                     context={'client_name': 'mycroft_listener'}))


def wait_for_dialog(bus, dialogs, context=None, timeout=None):
    """Wait for one of the dialogs given as argument.

    Args:
        bus (InterceptAllBusClient): Bus instance to listen on
        dialogs (list): list of acceptable dialogs
        context (behave Context): optional context providing scenario timeout
        timeout (int): how long to wait for the message, defaults to timeout
                       provided by context or 10 seconds
    """
    if context:
        timeout_duration = timeout or context.step_timeout
    else:
        timeout_duration = timeout or DEFAULT_TIMEOUT
    wait_for_dialog_match(bus, dialogs, timeout_duration)


def wait_for_dialog_match(bus, dialogs, timeout=DEFAULT_TIMEOUT):
    """Match dialogs spoken to the specified list of expected dialogs.

    Only one of the dialogs in the provided list need to match for this
    check to be successful.

    Args:
        bus (InterceptAllBusClient): Bus instance to listen on
        dialogs (list): list of acceptable dialogs
        timeout (int): how long to wait for the message, defaults to timeout
                       provided by context or 10 seconds

    Returns:
        A boolean indicating if a match was found and the list of "speak"
        events found on the message bus during the matching process.
    """
    match_found = False
    speak_messages = list()
    timeout_time = time.monotonic() + timeout
    while time.monotonic() < timeout_time:
        for message in bus.get_messages('speak'):
            speak_messages.append(message)
            dialog = message.data.get('meta', {}).get('dialog')
            if dialog in dialogs:
                wait_while_speaking()
                match_found = True
                break
        bus.clear_messages()
        if match_found:
            break
        time.sleep(1)

    return match_found, speak_messages


def wait_for_audio_service(context, message_type):
    """Wait for audio.service message that matches type provided.

    May be play, stop, or pause messages

    Args:
        context (behave Context): optional context providing scenario timeout
        message_type (string): final component of bus message in form
                               `mycroft.audio.service.{type}
    """
    msg_type = 'mycroft.audio.service.{}'.format(message_type)

    def check_for_msg(message):
        return message.msg_type == msg_type, ''

    passed, debug = then_wait(msg_type, check_for_msg, context)

    if not passed:
        debug += mycroft_responses(context)
    if not debug:
        if message_type == 'play':
            message_type = 'start'
        debug = "Mycroft didn't {} playback".format(message_type)

    assert passed, debug
