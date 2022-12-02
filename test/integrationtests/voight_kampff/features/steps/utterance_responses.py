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
"""
Predefined step definitions for handling dialog interaction with Mycroft for
use with behave.
"""
from os.path import join, exists, basename
from pathlib import Path
import re
from string import Formatter
import time

from behave import given, when, then

from mycroft.dialog import MustacheDialogRenderer
from mycroft.messagebus import Message
from mycroft.audio import wait_while_speaking
from mycroft.util.format import expand_options

from test.integrationtests.voight_kampff import (mycroft_responses, then_wait,
                                                 then_wait_fail)


def find_dialog(skill_path, dialog, lang):
    """Check the usual location for dialogs.

    TODO: subfolders
    """
    if exists(join(skill_path, 'dialog')):
        return join(skill_path, 'dialog', lang, dialog)
    else:
        return join(skill_path, 'locale', lang, dialog)


def load_dialog_file(dialog_path):
    """Load dialog files and get the contents."""
    renderer = MustacheDialogRenderer()
    renderer.load_template_file('template', dialog_path)
    expanded_lines = []
    for template in renderer.templates:
        # Expand parentheses in lines
        for line in renderer.templates[template]:
            expanded_lines += expand_options(line)
    return [line.strip().lower() for line in expanded_lines
            if line.strip() != '' and line.strip()[0] != '#']


def load_dialog_list(skill_path, dialog):
    """Load dialog from files into a single list.

    Args:
        skill (MycroftSkill): skill to load dialog from
        dialog (list): Dialog names (str) to load

    Returns:
        tuple (list of Expanded dialog strings, debug string)
    """
    dialog_path = find_dialog(skill_path, dialog)

    debug = 'Opening {}\n'.format(dialog_path)
    return load_dialog_file(dialog_path), debug


def _get_dialog_files(skill_path, lang):
    """Generator expression returning all dialog files.

    This includes both the 'locale' and the older style 'dialog' folder.

    Args:
        skill_path (str): skill root folder
        lang (str): language code to check

    yields:
        (Path) path of each found dialog file
    """
    in_dialog_dir = Path(skill_path, 'dialog', lang).rglob('*.dialog')
    for dialog_path in in_dialog_dir:
        yield dialog_path
    in_locale_dir = Path(skill_path, 'locale', lang).rglob('*.dialog')
    for dialog_path in in_locale_dir:
        yield dialog_path


def dialog_from_sentence(sentence, skill_path, lang):
    """Find dialog file from example sentence.

    Args:
        sentence (str): Text to match
        skill_path (str): path to skill directory
        lang (str): language code to use

    Returns (str): Dialog file best matching the sentence.
    """
    best = (None, 0)
    for path in _get_dialog_files(skill_path, lang):
        patterns = load_dialog_file(path)
        match, _ = _match_dialog_patterns(patterns, sentence.lower())
        if match is not False:
            if len(patterns[match]) > best[1]:
                best = (path, len(patterns[match]))
    if best[0] is not None:
        return basename(best[0])
    else:
        return None


def _match_dialog_patterns(dialogs, sentence):
    """Match sentence against a list of dialog patterns.

    dialogs (list of str): dialog file entries to match against
    sentence (str): string to match.

    Returns:
        (tup) index of found match, debug text
    """
    # Allow custom fields to be anything
    # i.e {field} gets turned into ".*"
    regexes = []
    for dialog in dialogs:
        data = {element[1]: '.*'
                for element in Formatter().parse(dialog)}
        regexes.append(dialog.format(**data))

    # Remove double whitespaces and ensure that it matches from
    # the beginning of the line.
    regexes = ['^' + ' '.join(reg.split()) for reg in regexes]
    debug = 'MATCHING: {}\n'.format(sentence)
    for index, regex in enumerate(regexes):
        match = re.match(regex, sentence)
        debug += '---------------\n'
        debug += '{} {}\n'.format(regex, match is not None)
        if match:
            return index, debug
    else:
        return False, debug


@given('an english speaking user')
def given_english(context):
    context.lang = 'en-us'


@given('a {timeout} seconds timeout')
@given('a {timeout} second timeout')
def given_timeout(context, timeout):
    """Set the timeout for the steps in this scenario."""
    context.step_timeout = float(timeout)


@given('a {timeout} minutes timeout')
@given('a {timeout} minute timeout')
def given_timeout(context, timeout):
    """Set the timeout for the steps in this scenario."""
    context.step_timeout = float(timeout) * 60


@when('the user says "{text}"')
def when_user_says(context, text):
    context.bus.emit(Message('recognizer_loop:utterance',
                             data={'utterances': [text],
                                   'lang': context.lang,
                                   'session': '',
                                   'ident': time.time()},
                             context={'client_name': 'mycroft_listener'}))


@then('"{skill}" should reply with dialog from "{dialog}"')
def then_dialog(context, skill, dialog):
    def check_dialog(message):
        utt_dialog = message.data.get('meta', {}).get('dialog')
        return (utt_dialog == dialog.replace('.dialog', ''), '')

    passed, debug = then_wait('speak', check_dialog, context)
    if not passed:
        assert_msg = debug
        assert_msg += mycroft_responses(context)

    assert passed, assert_msg or 'Mycroft didn\'t respond'


@then('"{skill}" should not reply')
def then_do_not_reply(context, skill):

    def check_all_dialog(message):
        msg_skill = message.data.get('meta').get('skill')
        utt = message.data['utterance'].lower()
        skill_responded = skill == msg_skill
        debug_msg = ("{} responded with '{}'. \n".format(skill, utt)
                     if skill_responded else '')
        return (skill_responded, debug_msg)

    passed, debug = then_wait_fail('speak', check_all_dialog, context)
    if not passed:
        assert_msg = debug
        assert_msg += mycroft_responses(context)
    assert passed, assert_msg or '{} responded'.format(skill)


@then('"{skill}" should reply with "{example}"')
def then_example(context, skill, example):
    skill_path = context.msm.find_skill(skill).path
    dialog = dialog_from_sentence(example, skill_path, context.lang)
    print('Matching with the dialog file: {}'.format(dialog))
    assert dialog is not None, 'No matching dialog...'
    then_dialog(context, skill, dialog)


@then('"{skill}" should reply with anything')
def then_anything(context, skill):
    def check_any_messages(message):
        debug = ''
        result = message is not None
        return (result, debug)

    passed = then_wait('speak', check_any_messages, context)
    assert passed, 'No speech received at all'


@then('"{skill}" should reply with exactly "{text}"')
def then_exactly(context, skill, text):
    def check_exact_match(message):
        utt = message.data['utterance'].lower()
        debug = 'Comparing {} with expected {}\n'.format(utt, text)
        result = utt == text.lower()
        return (result, debug)

    passed, debug = then_wait('speak', check_exact_match, context)
    if not passed:
        assert_msg = debug
        assert_msg += mycroft_responses(context)
    assert passed, assert_msg


@then('"{skill}" reply should contain "{text}"')
@then('mycroft reply should contain "{text}"')
def then_contains(context, text):
    def check_contains(message):
        utt = message.data['utterance'].lower()
        debug = 'Checking if "{}" contains "{}"\n'.format(utt, text)
        result = text.lower() in utt
        return (result, debug)

    passed, debug = then_wait('speak', check_contains, context)

    if not passed:
        assert_msg = 'No speech contained the expected content'
        assert_msg += mycroft_responses(context)

    assert passed, assert_msg


@then('the user replies with "{text}"')
@then('the user replies "{text}"')
@then('the user says "{text}"')
def then_user_follow_up(context, text):
    """Send a user response after being prompted by device.

    The sleep after the device is finished speaking is to address a race
    condition in the MycroftSkill base class conversational code.  It can
    be removed when the race condition is addressed.
    """
    wait_while_speaking()
    time.sleep(2)
    context.bus.emit(Message('recognizer_loop:utterance',
                             data={'utterances': [text],
                                   'lang': context.lang,
                                   'session': '',
                                   'ident': time.time()},
                             context={'client_name': 'mycroft_listener'}))


@then('mycroft should send the message "{message_type}"')
def then_messagebus_message(context, message_type):
    """Verify a specific message is sent."""
    def check_dummy(message):
        """We are just interested in the message data, just the type."""
        return True, ""

    message_found, _ = then_wait(message_type, check_dummy, context)
    assert message_found, "No matching message received."
