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
from typing import Any, Callable, List, Tuple
import time

from mycroft.audio.utils import wait_while_speaking
from mycroft.messagebus import Message

DEFAULT_TIMEOUT = 10


class VoightKampffMessageMatcher:
    """Matches a specified message type to messages emitted on the bus.

    Usage:
        Intended for use in a single test condition.

        matcher = VoightKampffMessageMatcher(message_type, context)
        match_found, error_message = matcher.match()
        assert match_found, error_message

    Attributes:
        message_type: identifier of the message to search for on the bus
        context: the Behave context from the test utilizing this class
        match_event: mechanism for knowing when a match is found
        error_message: message that can be used by the test to communicate
            the reason for a failed match to the tester.
    """
    def __init__(self, context: Any, message_type: str):
        self.message_type = message_type
        self.context = context
        self.match_event = Event()
        self.error_message = ""

    @property
    def match_found(self):
        return self.match_event.is_set()

    def match(self, timeout: int = None):
        """Attempts to match the requested message type to emitted bus events.

        Use a message bus event handler to capture any message emitted on the
        bus that matches the message type specified by the caller.  Also
        checks any messages emitted prior to the handler being defined to
        protect against a race condition.

        Args:
            timeout: number of seconds to attempt matching before giving up
        """
        timeout = timeout or self.context.step_timeout
        self.context.bus.on(self.message_type, self.handle_message)
        self._check_historical_messages()
        if not self.match_event.is_set():
            self.match_event.wait(timeout=timeout)
        self.context.bus.remove(self.message_type, self.handle_message)
        if not self.match_found:
            self._build_error_message()

        return self.match_found, self.error_message

    def _check_historical_messages(self):
        """Searches messages emitted before the event handler was defined."""
        for message in self.context.bus.get_messages(self.message_type):
            self.handle_message(message)
            if self.match_found:
                break
        self.context.bus.clear_messages()

    def handle_message(self, message: Message):
        """Applies matching criteria to the emitted event.

        Args:
            message: message emitted by bus with the requested message type
        """
        self.context.matched_message = message
        self.match_event.set()

    def _build_error_message(self):
        """Builds a message that communicates the failure to the test."""
        self.error_message = (
            f"Expected message type {self.message_type} was not emitted."
        )


class VoightKampffDialogMatcher(VoightKampffMessageMatcher):
    """Variation of VoightKampffEventMatcher for matching dialogs.

    Usage:
        Intended for use in a single test condition.

        matcher = VoightKampffDialogMatcher(context, dialogs)
        match_found, error_message = matcher.match()
        assert match_found, error_message

    Attributes:
        dialogs: one or more dialog names that will constitute a match
        speak_messages: bus messages with message type of "speak" captured
            in the matching process
    """
    def __init__(self, context: Any, dialogs: List[str]):
        super().__init__(context, message_type="speak")
        self.dialogs = dialogs
        self.speak_messages = list()

    def handle_message(self, message: Message):
        """Applies matching criteria to the emitted event.

        Args:
            message: message emitted by bus with the requested message type
        """
        self.speak_messages.append(message)
        dialog = message.data.get('meta', {}).get('dialog')
        if dialog in self.dialogs:
            wait_while_speaking()
            self.context.matched_message = message
            self.match_event.set()

    def _build_error_message(self):
        """Builds a message that communicates the failure to the test."""
        self.error_message = (
            'Expected Mycroft to respond with one of:\n'
            f"\t{', '.join(self.dialogs)}\n"
            "Actual response(s):\n"
        )
        if self.speak_messages:
            for message in self.speak_messages:
                meta = message.data.get("meta")
                if meta is not None:
                    if 'dialog' in meta:
                        self.error_message += f"\tDialog: {meta['dialog']}"
                    if 'skill' in meta:
                        self.error_message += (
                            f" (from {meta['skill']} skill)\n"
                        )
        else:
            self.error_message += "\tMycroft didn't respond"


class VoightKampffCriteriaMatcher(VoightKampffMessageMatcher):
    """Variation of VoightKampffEventMatcher for matching event data.

    In some cases, matching the message type is not enough.  The test
    requires data in the message payload to match a specified criteria
    to pass.

    Usage:
        Intended for use in a single test condition.

        matcher = VoightKampffCriteriaMatcher(
        message_type, context, criteria_matcher
        )
        match_found, error_message = matcher.match()
        assert match_found, error_message

    Attributes:
        criteria_matcher: Function to determine if a message contains
            the data necessary for the test case to pass
    """
    def __init__(self, context: Any, message_type: str,
                 criteria_matcher: Callable):
        super().__init__(context, message_type)
        self.criteria_matcher = criteria_matcher
        self.error_message = ""

    def handle_message(self, message: Message):
        """Applies matching criteria to the emitted event.

        Args:
            message: message emitted by bus with the requested message type
        """
        status, error_message = self.criteria_matcher(message)
        self.error_message += error_message
        if status:
            self.context.matched_message = message
            self.match_event.set()

    def _build_error_message(self):
        """Builds a message that communicates the failure to the test."""
        # The error message is built from the return value of the criteria
        # matcher so this method is not needed.
        pass


# TODO: Remove in 21.08
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


def then_wait(msg_type: str, criteria_func: Callable, context: Any,
              timeout: int = None) -> Tuple[bool, str]:
    """Wait for a specific message type to fulfill a criteria.

    Args:
        msg_type: message type to watch
        criteria_func: Function to determine if a message fulfilling the
                       test case has been found.
        context: behave context
        timeout: Time allowance for a message fulfilling the criteria, if
                 provided will override the normal normal step timeout.

    Returns:
        The success of the match attempt and an error message.
    """
    matcher = VoightKampffCriteriaMatcher(context, msg_type, criteria_func)
    match_found, error_message = matcher.match(timeout)

    return match_found, error_message


def then_wait_fail(msg_type: str, criteria_func: Callable, context: Any,
                   timeout: int = None) -> Tuple[bool, str]:
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
    match_found, error_message = then_wait(msg_type, criteria_func,
                                           context, timeout)
    return not match_found, error_message


# TODO: remove in 21.08
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


# TODO: remove in 21.08
def print_mycroft_responses(context):
    print(mycroft_responses(context))


# TODO: remove in 21.08
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


# TODO: remove in 21.08
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


# TODO: remove in 21.08
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


def wait_for_audio_service(context: Any, message_type: str):
    """Wait for audio.service message that matches type provided.

    May be play, stop, or pause messages

    Args:
        context: optional context providing scenario timeout
        message_type: final component of bus message in form
            mycroft.audio.service.{type}

    Raises:
        AssertionError if no match is found.
    """
    msg_type = 'mycroft.audio.service.{}'.format(message_type)
    event_matcher = VoightKampffMessageMatcher(context, msg_type)
    match_found, error_message = event_matcher.match()

    assert match_found, error_message
