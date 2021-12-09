# Copyright 2019 Mycroft AI Inc.
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
"""A collection of rules for the skill tester."""
import re

from mycroft.util.format import expand_options

from .colors import color


def intent_type_check(intent_type):
    return (['or'] +
            [['endsWith', 'intent_type', intent_type]] +
            [['endsWith', '__type__', intent_type]])


def play_query_check(skill, match, phrase):
    d = ['and']
    d.append(['equal', '__type__', 'query'])
    d.append(['equal', 'skill_id', skill.skill_id])
    d.append(['equal', 'phrase', phrase])
    d.append(['gt', 'conf', match.get('confidence_threshold', 0.5)])
    return d


def question_check(skill, question, expected_answer):
    d = ['and']
    d.append(['equal', '__type__', 'query.response'])
    d.append(['equal', 'skill_id', skill.skill_id])
    d.append(['equal', 'phrase', question])
    d.append(['match', 'answer', expected_answer])
    return d


def expected_data_check(expected_items):
    d = ['and']
    for item in expected_items:
        d.append(['equal', item[0], item[1]])
    return d


def load_dialog_list(skill, dialog):
    """ Load dialog from files into a single list.

    Args:
        skill (MycroftSkill): skill to load dialog from
        dialog (list): Dialog names (str) to load

    Returns:
        list: Expanded dialog strings
    """
    dialogs = []
    try:
        for d in dialog:
            for e in skill.dialog_renderer.templates[d]:
                dialogs += expand_options(e)
    except Exception as template_load_exception:
        print(color.FAIL +
              "Failed to load dialog template " +
              "'dialog/en-us/" + d + ".dialog'" +
              color.RESET)
        raise Exception("Can't load 'excepted_dialog': "
                        "file '" + d + ".dialog'") \
            from template_load_exception
    return dialogs


def expected_dialog_check(expected_dialog, skill):
    # Check that expected dialog file is used
    if isinstance(expected_dialog, str):
        dialog = [expected_dialog]  # Make list
    else:
        dialog = expected_dialog
    # Extract dialog texts from skill
    dialogs = load_dialog_list(skill, dialog)
    # Allow custom fields to be anything
    d = [re.sub(r'{.*?\}', r'.*', t) for t in dialogs]
    # Merge consequtive .*'s into a single .*
    d = [re.sub(r'\.\*( \.\*)+', r'.*', t) for t in d]

    # Create rule allowing any of the sentences for that dialog
    return [['match', 'utterance', r] for r in d]


def changed_context_check(ctx):
    if not isinstance(ctx, list):
        ctx = [ctx]
    return [['endsWith', 'context', str(c)] for c in ctx]
