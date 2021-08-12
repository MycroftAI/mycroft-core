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
"""The module execute a test of one skill intent.

Using a mocked message bus this module is responsible for sending utterences
and testing that the intent is called.

The module runner can test:
    That the expected intent in the skill is activated
    That the expected parameters are extracted from the utterance
    That Mycroft contexts are set or removed
    That the skill speak the intended answer
    The content of any message exchanged between the skill and the mycroft core

To set up a test the test runner can
    Send an utterance, as the user would normally speak
    Set up and remove context
    Set up a custom timeout for the test runner, to allow for skills that runs
    for a very long time

"""
from queue import Queue, Empty
from copy import copy
import json
import time
import os
import re
import ast
from os.path import join, isdir, basename
from pyee import EventEmitter
from numbers import Number
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill, FallbackSkill
from mycroft.skills.skill_loader import SkillLoader
from mycroft.configuration import Configuration
from mycroft.util.log import LOG

from logging import StreamHandler
from io import StringIO
from contextlib import contextmanager

from .colors import color
from .rules import (intent_type_check, play_query_check, question_check,
                    expected_data_check, expected_dialog_check,
                    changed_context_check)

MainModule = '__init__'

DEFAULT_EVALUAITON_TIMEOUT = 30

# Set a configuration value to allow skills to check if they're in a test
Configuration.get()['test_env'] = True


class SkillTestError(Exception):
    pass


@contextmanager
def temporary_handler(log, handler):
    """Context manager to replace the default logger with a temporary logger.

    Args:
        log (LOG): mycroft LOG object
        handler (logging.Handler): Handler object to use
    """
    old_handler = log.handler
    log.handler = handler
    yield
    log.handler = old_handler


def create_skill_descriptor(skill_path):
    return {"path": skill_path}


def get_skills(skills_folder):
    """Find skills in the skill folder or sub folders.

        Recursive traversal into subfolders stop when a __init__.py file
        is discovered

        Args:
            skills_folder:  Folder to start a search for skills __init__.py
                            files

        Returns:
            list: the skills
    """

    skills = []

    def _get_skill_descriptor(skills_folder):
        if not isdir(skills_folder):
            return
        if MainModule + ".py" in os.listdir(skills_folder):
            skills.append(create_skill_descriptor(skills_folder))
            return

        possible_skills = os.listdir(skills_folder)
        for i in possible_skills:
            _get_skill_descriptor(join(skills_folder, i))

    _get_skill_descriptor(skills_folder)

    skills = sorted(skills, key=lambda p: basename(p['path']))
    return skills


def load_skills(emitter, skills_root):
    """Load all skills and set up emitter

        Args:
            emitter: The emmitter to use
            skills_root: Directory of the skills __init__.py

        Returns:
            tuple: (list of loaded skills, dict with logs for each skill)

    """
    skill_list = []
    log = {}
    for skill in get_skills(skills_root):
        path = skill["path"]
        skill_id = 'test-' + basename(path)

        # Catch the logs during skill loading
        from mycroft.util.log import LOG as skills_log
        buf = StringIO()
        with temporary_handler(skills_log, StreamHandler(buf)):
            skill_loader = SkillLoader(emitter, path)
            skill_loader.skill_id = skill_id
            skill_loader.load()
            skill_list.append(skill_loader.instance)

        # Restore skill logger since it was created with the temporary handler
        if skill_loader.instance:
            skill_loader.instance.log = LOG.create_logger(
                skill_loader.instance.name)
        log[path] = buf.getvalue()

    return skill_list, log


def unload_skills(skills):
    for s in skills:
        s.default_shutdown()


class InterceptEmitter(object):
    """
    This class intercepts and allows emitting events between the
    skill_tester and the skill being tested.
    When a test is running emitted communication is intercepted for analysis
    """

    def __init__(self):
        self.emitter = EventEmitter()
        self.q = None

    def on(self, event, f):
        # run all events
        print("Event: ", event)
        self.emitter.on(event, f)

    def emit(self, event, *args, **kwargs):
        event_name = event.msg_type
        if self.q:
            self.q.put(event)
        self.emitter.emit(event_name, event, *args, **kwargs)

    def wait_for_response(self, event, reply_type=None, *args, **kwargs):
        """Simple single thread implementation of wait_for_response."""
        message_type = reply_type or event.msg_type + '.response'
        response = None

        def response_handler(msg):
            nonlocal response
            response = msg

        self.emitter.once(message_type, response_handler)
        self.emitter.emit(event.msg_type, event)
        return response

    def once(self, event, f):
        self.emitter.once(event, f)

    def remove(self, event_name, func):
        pass

    def remove_all_listeners(self, event_name):
        pass


class MockSkillsLoader(object):
    """Load a skill and set up emitter
    """

    def __init__(self, skills_root):
        self.load_log = None

        self.skills_root = skills_root
        self.emitter = InterceptEmitter()
        from mycroft.skills.intent_service import IntentService
        self.ih = IntentService(self.emitter)
        self.skills = None
        self.emitter.on(
            'mycroft.skills.fallback',
            FallbackSkill.make_intent_failure_handler(self.emitter))

        def make_response(message):
            skill_id = message.data.get('skill_id', '')
            data = dict(result=False, skill_id=skill_id)
            self.emitter.emit(Message('skill.converse.response', data))
        self.emitter.on('skill.converse.request', make_response)

    def load_skills(self):
        skills, self.load_log = load_skills(self.emitter, self.skills_root)
        self.skills = [s for s in skills if s]
        self.ih.padatious_service.train(
            Message('', data=dict(single_thread=True)))
        return self.emitter.emitter  # kick out the underlying emitter

    def unload_skills(self):
        unload_skills(self.skills)


def load_test_case_file(test_case_file):
    """Load a test case to run."""
    print("")
    print(color.HEADER + "="*20 + " RUNNING TEST " + "="*20 + color.RESET)
    print('Test file: ', test_case_file)
    with open(test_case_file, 'r') as f:
        test_case = json.load(f)
    print('Test:', json.dumps(test_case, indent=4, sort_keys=False))
    return test_case


class SkillTest(object):
    """
        This class is instantiated for each skill being tested. It holds the
        data needed for the test, and contains the methods doing the test

    """

    def __init__(self, skill, test_case_file, emitter, test_status=None):
        self.skill = skill
        self.test_case_file = test_case_file
        self.emitter = emitter
        self.dict = dict
        self.output_file = None
        self.returned_intent = False
        self.test_status = test_status
        self.failure_msg = None
        self.end_of_skill = False

    def run(self, loader):
        """ Execute the test

        Run a test for a skill. The skill, test_case_file and emitter is
        already set up in the __init__ method.

        This method does all the preparation and cleanup and calls
        self.execute_test() to perform the actual test.

        Args:
            bool: Test results -- only True if all passed
        """
        self.end_of_skill = False  # Reset to false at beginning of test

        s = [s for s in loader.skills if s and s.root_dir == self.skill]
        if s:
            s = s[0]
        else:
            # The skill wasn't loaded, print the load log for the skill
            if self.skill in loader.load_log:
                print('\n {} Captured Logs from loading {}'.format('=' * 15,
                                                                   '=' * 15))
                print(loader.load_log.pop(self.skill))

            raise SkillTestError('Skill couldn\'t be loaded')

        orig_get_response = s.get_response
        original_settings = s.settings
        try:
            return self.execute_test(s)
        finally:
            s.get_response = orig_get_response
            s.settings = original_settings

    def send_play_query(self, s, test_case):
        """Emit an event triggering the a check for playback possibilities."""
        play_query = test_case['play_query']
        print('PLAY QUERY', color.USER_UTT + play_query + color.RESET)
        self.emitter.emit('play:query', Message('play:query:',
                                                {'phrase': play_query}))

    def send_play_start(self, s, test_case):
        """Emit an event starting playback from the skill."""
        print('PLAY START')
        callback_data = test_case['play_start']
        callback_data['skill_id'] = s.skill_id
        self.emitter.emit('play:start',
                          Message('play:start', callback_data))

    def send_question(self, test_case):
        """Emit a Question to the loaded skills."""
        print("QUESTION: {}".format(test_case['question']))
        callback_data = {'phrase': test_case['question']}
        self.emitter.emit('question:query',
                          Message('question:query', data=callback_data))

    def send_utterance(self, test_case):
        """Emit an utterance to the loaded skills."""
        utt = test_case['utterance']
        print("UTTERANCE:", color.USER_UTT + utt + color.RESET)
        self.emitter.emit('recognizer_loop:utterance',
                          Message('recognizer_loop:utterance',
                                  {'utterances': [utt]}))

    def apply_test_settings(self, s, test_case):
        """Replace the skills settings with settings from the test_case."""
        s.settings = copy(test_case['settings'])
        print(color.YELLOW, 'will run test with custom settings:',
                            '\n{}'.format(s.settings), color.RESET)

    def setup_get_response(self, s, test_case):
        """Setup interception of get_response calls."""
        def get_response(dialog='', data=None, announcement='',
                         validator=None, on_fail=None, num_retries=-1):
            data = data or {}
            utt = announcement or s.dialog_renderer.render(dialog, data)
            print(color.MYCROFT + ">> " + utt + color.RESET)
            s.speak(utt)

            response = test_case['responses'].pop(0)
            print("SENDING RESPONSE:",
                  color.USER_UTT + response + color.RESET)
            return response

        s.get_response = get_response

    def remove_context(self, s, cxt):
        """remove an adapt context."""
        if isinstance(cxt, list):
            for x in cxt:
                MycroftSkill.remove_context(s, x)
        else:
            MycroftSkill.remove_context(s, cxt)

    def set_context(self, s, cxt):
        """Set an adapt context."""
        for key, value in cxt.items():
            MycroftSkill.set_context(s, key, value)

    def send_test_input(self, s, test_case):
        """Emit an utterance, just like the STT engine does. This sends the
        provided text to the skill engine for intent matching and it then
        invokes the skill.

        It also handles some special cases for common play skills and common
        query skills.
        """
        if 'utterance' in test_case:
            self.send_utterance(test_case)
        elif 'play_query' in test_case:
            self.send_play_query(s, test_case)
        elif 'play_start' in test_case:
            self.send_play_start(s, test_case)
        elif 'question' in test_case:
            self.send_question(test_case)
        else:
            raise SkillTestError('No input provided in test case')

    def execute_test(self, s):
        """ Execute test case.

        Args:
            s (MycroftSkill): mycroft skill to test

        Returns:
            (bool) True if the test succeeded completely.
        """
        test_case = load_test_case_file(self.test_case_file)

        if 'settings' in test_case:
            self.apply_test_settings(s, test_case)

        if 'responses' in test_case:
            self.setup_get_response(s, test_case)

        # If we keep track of test status for the entire skill, then
        # get all intents from the skill, and mark current intent
        # tested
        if self.test_status:
            self.test_status.append_intent(s)
            if 'intent_type' in test_case:
                self.test_status.set_tested(test_case['intent_type'])

        evaluation_rule = EvaluationRule(test_case, s)

        # Set up queue for emitted events. Because
        # the evaluation method expects events to be received in convoy,
        # and be handled one by one. We cant make assumptions about threading
        # in the core or the skill
        q = Queue()
        s.bus.q = q

        # Set up context before calling intent
        # This option makes it possible to better isolate (reduce dependance)
        # between test_cases
        cxt = test_case.get('remove_context', None)
        if cxt:
            self.remove_context(s, cxt)

        cxt = test_case.get('set_context', None)
        if cxt:
            self.set_context(s, cxt)

        self.send_test_input(s, test_case)
        # Wait up to X seconds for the test_case to complete
        timeout = self.get_timeout(test_case)

        while not evaluation_rule.all_succeeded():
            # Process the queue until a skill handler sends a complete message
            if self.check_queue(q, evaluation_rule) or time.time() > timeout:
                break

        self.shutdown_emitter(s)

        # Report test result if failed
        return self.results(evaluation_rule)

    def get_timeout(self, test_case):
        """Find any timeout specified in test case.

        If no timeout is specified return the default.
        """
        if (test_case.get('evaluation_timeout', None) and
                isinstance(test_case['evaluation_timeout'], int)):
            return time.time() + int(test_case.get('evaluation_timeout'))
        else:
            return time.time() + DEFAULT_EVALUAITON_TIMEOUT

    def check_queue(self, q, evaluation_rule):
        """Check the queue for events.

        If event indicating skill completion is found returns True, else False.
        """
        try:
            event = q.get(timeout=1)
            if ':' in event.msg_type:
                event.data['__type__'] = event.msg_type.split(':')[1]
            else:
                event.data['__type__'] = event.msg_type

            evaluation_rule.evaluate(event.data)
            if event.msg_type == 'mycroft.skill.handler.complete':
                self.end_of_skill = True
        except Empty:
            pass

        if q.empty() and self.end_of_skill:
            return True
        else:
            return False

    def shutdown_emitter(self, s):
        """Shutdown the skill connection to the bus."""
        # Stop emiter from sending on queue
        s.bus.q = None

        # remove the skill which is not responding
        self.emitter.remove_all_listeners('speak')
        self.emitter.remove_all_listeners('mycroft.skill.handler.complete')

    def results(self, evaluation_rule):
        """Display and report the results."""
        if not evaluation_rule.all_succeeded():
            self.failure_msg = str(evaluation_rule.get_failure())
            print(color.FAIL + "Evaluation failed" + color.RESET)
            print(color.FAIL + "Failure:", self.failure_msg + color.RESET)
            return False

        return True


# Messages that should not print debug info
HIDDEN_MESSAGES = ['skill.converse.request', 'skill.converse.response',
                   'gui.page.show', 'gui.value.set']


class EvaluationRule:
    """
        This class initially convert the test_case json file to internal rule
        format, which is stored throughout the testcase run. All Messages on
        the event bus can be evaluated against the rules (test_case)

        This approach makes it easier to add new tests, since Message and rule
        traversal is already set up for the internal rule format.
        The test writer can use the internal rule format directly in the
        test_case using the assert keyword, which allows for more
        powerfull/individual test cases than the standard dictionaly
    """

    def __init__(self, test_case, skill=None):
        """ Convert test_case read from file to internal rule format

        Args:
            test_case:  The loaded test case
            skill:      optional skill to test, used to fetch dialogs
        """
        self.rule = []

        _x = ['and']
        if 'utterance' in test_case and 'intent_type' in test_case:
            intent_type = str(test_case['intent_type'])
            _x.append(intent_type_check(intent_type))

        # Check for adapt intent info
        if test_case.get('intent', None):
            for item in test_case['intent'].items():
                _x.append(['equal', str(item[0]), str(item[1])])

        if 'play_query_match' in test_case:
            match = test_case['play_query_match']
            phrase = match.get('phrase', test_case.get('play_query'))
            self.rule.append(play_query_check(skill, match, phrase))
        elif 'expected_answer' in test_case:
            question = test_case['question']
            expected_answer = test_case['expected_answer']
            self.rule.append(question_check(skill, question, expected_answer))

        # Check for expected data structure
        if test_case.get('expected_data'):
            expected_items = test_case['expected_data'].items()
            self.rule.append(expected_data_check(expected_items))

        if _x != ['and']:
            self.rule.append(_x)

        # Add rules from expeceted_response
        # Accepts a string or a list of multiple strings
        if isinstance(test_case.get('expected_response', None), str):
            self.rule.append(['match', 'utterance',
                              str(test_case['expected_response'])])
        elif isinstance(test_case.get('expected_response', None), list):
            texts = test_case['expected_response']
            rules = [['match', 'utterance', str(r)] for r in texts]
            self.rule.append(['or'] + rules)

        # Add rules from expected_dialog
        # Accepts dialog (without ".dialog"), the same way as self.speak_dialog
        # as a string or a list of dialogs
        if test_case.get('expected_dialog', None):
            if not skill:
                print(color.FAIL +
                      'Skill is missing, can\'t run expected_dialog test' +
                      color.RESET)
            else:
                expected_dialog = test_case['expected_dialog']
                self.rule.append(['or'] +
                                 expected_dialog_check(expected_dialog,
                                                       skill))

        if test_case.get('changed_context', None):
            ctx = test_case['changed_context']
            for c in changed_context_check(ctx):
                self.rule.append(c)

        if test_case.get('assert', None):
            for _x in ast.literal_eval(test_case['assert']):
                self.rule.append(_x)

        print("Rule created ", self.rule)

    def evaluate(self, msg):
        """ Main entry for evaluating a message against the rules.

        The rules are prepared in the __init__
        This method is usually called several times with different
        messages using the same rule set. Each call contributing
        to fulfilling all the rules

        Args:
            msg:  The message event to evaluate
        """
        if msg.get('__type__', '') not in HIDDEN_MESSAGES:
            print("\nEvaluating message: ", msg)
        for r in self.rule:
            self._partial_evaluate(r, msg)

    def _get_field_value(self, rule, msg):
        if isinstance(rule, list):
            value = msg.get(rule[0], None)
            if len(rule) > 1 and value:
                for field in rule[1:]:
                    value = value.get(field, None)
                    if not value:
                        break
        else:
            value = msg.get(rule, None)

        return value

    def _partial_evaluate(self, rule, msg):
        """ Evaluate the message against a part of the rules

        Recursive over rules

        Args:
            rule:  A rule or a part of the rules to be broken down further
            msg:   The message event being evaluated

        Returns:
            Bool: True if a partial evaluation succeeded
        """
        if 'succeeded' in rule:  # Rule has already succeeded, test not needed
            return True

        if rule[0] == 'equal':
            if self._get_field_value(rule[1], msg) != rule[2]:
                return False

        if rule[0] == 'lt':
            if not isinstance(self._get_field_value(rule[1], msg), Number):
                return False
            if self._get_field_value(rule[1], msg) >= rule[2]:
                return False

        if rule[0] == 'gt':
            if not isinstance(self._get_field_value(rule[1], msg), Number):
                return False
            if self._get_field_value(rule[1], msg) <= rule[2]:
                return False

        if rule[0] == 'notEqual':
            if self._get_field_value(rule[1], msg) == rule[2]:
                return False

        if rule[0] == 'endsWith':
            if not (self._get_field_value(rule[1], msg) and
                    self._get_field_value(rule[1], msg).endswith(rule[2])):
                return False

        if rule[0] == 'exists':
            if not self._get_field_value(rule[1], msg):
                return False

        if rule[0] == 'match':
            if not (self._get_field_value(rule[1], msg) and
                    re.match(rule[2], self._get_field_value(rule[1], msg))):
                return False

        if rule[0] == 'and':
            for i in rule[1:]:
                if not self._partial_evaluate(i, msg):
                    return False

        if rule[0] == 'or':
            for i in rule[1:]:
                if self._partial_evaluate(i, msg):
                    break
            else:
                return False
        rule.append('succeeded')
        return True

    def get_failure(self):
        """ Get the first rule which has not succeeded

        Returns:
            str: The failed rule
        """
        for x in self.rule:
            if x[-1] != 'succeeded':
                return x
        return None

    def all_succeeded(self):
        """ Test if all rules succeeded

        Returns:
            bool: True if all rules succeeded
        """
        return len([x for x in self.rule if x[-1] != 'succeeded']) == 0
