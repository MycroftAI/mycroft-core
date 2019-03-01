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
import json
import time
import os
import re
import ast
from os.path import join, isdir, basename
from pyee import EventEmitter
from numbers import Number
from mycroft.messagebus.message import Message
from mycroft.skills.core import create_skill_descriptor, load_skill, \
    MycroftSkill, FallbackSkill
from mycroft.skills.settings import SkillSettings
from mycroft.configuration import Configuration

from logging import StreamHandler
from io import StringIO
from contextlib import contextmanager

MainModule = '__init__'

DEFAULT_EVALUAITON_TIMEOUT = 30

# Set a configuration value to allow skills to check if they're in a test
Configuration.get()['test_env'] = True


class SkillTestError(Exception):
    pass


# Easy way to show colors on terminals
class clr:
    PINK = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    DKGRAY = '\033[90m'
    # Classes
    USER_UTT = '\033[96m'  # cyan
    MYCROFT = '\033[33m'   # bright yellow
    HEADER = '\033[94m'    # blue
    WARNING = '\033[93m'   # yellow
    FAIL = '\033[91m'      # red
    RESET = '\033[0m'


class no_clr:
    PINK = ''
    BLUE = ''
    CYAN = ''
    GREEN = ''
    YELLOW = ''
    RED = ''
    DKGRAY = ''
    USER_UTT = ''
    MYCROFT = ''
    HEADER = ''
    WARNING = ''
    FAIL = ''
    RESET = ''


# MST as in Mycroft Skill Tester
if 'MST_NO_COLOR' not in os.environ:
    color = clr
else:
    color = no_clr


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
        from mycroft.skills.core import LOG as skills_log
        buf = StringIO()
        with temporary_handler(skills_log, StreamHandler(buf)):
            skill_list.append(load_skill(skill, emitter, skill_id))
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
        event_name = event.type
        if self.q:
            self.q.put(event)
        self.emitter.emit(event_name, event, *args, **kwargs)

    def once(self, event, f):
        self.emitter.once(event, f)

    def remove(self, event_name, func):
        pass

    def remove_all_listeners(self, event_name):
        pass


class TestSettings(SkillSettings):
    """ SkillSettings instance without saving/loading capability.
    """
    def save_skill_settings(self, skill_settings):
        pass

    def _poll_skill_settings(self):
        pass

    def _load_settings_meta(self):
        return None

    def update(self, settings_meta):
        pass

    def load_skill_settings_from_file(self):
        pass

    def store(self, force=False):
        pass


class MockSkillsLoader(object):
    """Load a skill and set up emitter
    """

    def __init__(self, skills_root):
        self.load_log = None

        self.skills_root = skills_root
        self.emitter = InterceptEmitter()
        from mycroft.skills.intent_service import IntentService
        from mycroft.skills.padatious_service import PadatiousService
        self.ih = IntentService(self.emitter)
        self.ps = PadatiousService(self.emitter, self.ih)
        self.skills = None
        self.emitter.on(
            'intent_failure',
            FallbackSkill.make_intent_failure_handler(self.emitter))

        def make_response(message):
            skill_id = message.data.get('skill_id', '')
            data = dict(result=False, skill_id=skill_id)
            self.emitter.emit(Message('skill.converse.response', data))
        self.emitter.on('skill.converse.request', make_response)

    def load_skills(self):
        skills, self.load_log = load_skills(self.emitter, self.skills_root)
        self.skills = [s for s in skills if s]
        self.ps.train(Message('', data=dict(single_thread=True)))
        return self.emitter.emitter  # kick out the underlying emitter

    def unload_skills(self):
        unload_skills(self.skills)


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

    def run(self, loader):
        """
            Run a test for a skill. The skill, test_case_file and emitter is
            already set up in the __init__ method

            Args:
                loader:  A list of loaded skills
        """
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

        print("")
        print(color.HEADER + "="*20 + " RUNNING TEST " + "="*20 + color.RESET)
        print('Test file: ', self.test_case_file)
        with open(self.test_case_file, 'r') as f:
            test_case = json.load(f)
        print('Test:', json.dumps(test_case, indent=4, sort_keys=False))

        original_settings = None
        if 'settings' in test_case:
            original_settings = s.settings
            s.settings = TestSettings('/tmp/', self.test_case_file)
            for key in test_case['settings']:
                s.settings[key] = test_case['settings'][key]
            print(color.YELLOW, 'will run test with custom settings:',
                  '\n{}'.format(s.settings), color.RESET)

        if 'responses' in test_case:
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
            if isinstance(cxt, list):
                for x in cxt:
                    MycroftSkill.remove_context(s, x)
            else:
                MycroftSkill.remove_context(s, cxt)

        cxt = test_case.get('set_context', None)
        if cxt:
            for key, value in cxt.items():
                MycroftSkill.set_context(s, key, value)

        # Emit an utterance, just like the STT engine does.  This sends the
        # provided text to the skill engine for intent matching and it then
        # invokes the skill.
        utt = test_case.get('utterance', None)
        play_utt = test_case.get('play_query', None)
        play_start = test_case.get('play_start', None)
        if utt:
            print("UTTERANCE:", color.USER_UTT + utt + color.RESET)
            self.emitter.emit(
                'recognizer_loop:utterance',
                Message('recognizer_loop:utterance',
                        {'utterances': [utt]}))
        elif play_utt:
            print('PLAY QUERY', color.USER_UTT + play_utt + color.RESET)
            self.emitter.emit('play:query', Message('play:query:',
                                                    {'phrase': play_utt}))
        elif play_start:
            print('PLAY START')
            callback_data = play_start
            callback_data['skill_id'] = s.skill_id
            self.emitter.emit('play:start',
                              Message('play:start', callback_data))
        else:
            raise SkillTestError('No input utterance provided')

        # Wait up to X seconds for the test_case to complete
        timeout = time.time() + int(test_case.get('evaluation_timeout')) \
            if test_case.get('evaluation_timeout', None) and \
            isinstance(test_case['evaluation_timeout'], int) \
            else time.time() + DEFAULT_EVALUAITON_TIMEOUT
        while not evaluation_rule.all_succeeded():
            try:
                event = q.get(timeout=1)
                if ':' in event.type:
                    event.data['__type__'] = event.type.split(':')[1]
                else:
                    event.data['__type__'] = event.type

                evaluation_rule.evaluate(event.data)
                if event.type == 'mycroft.skill.handler.complete':
                    break
            except Empty:
                pass
            if time.time() > timeout:
                break

        # Stop emmiter from sending on queue
        s.bus.q = None

        # remove the skill which is not responding
        self.emitter.remove_all_listeners('speak')
        self.emitter.remove_all_listeners('mycroft.skill.handler.complete')
        # Report test result if failed
        if not evaluation_rule.all_succeeded():
            self.failure_msg = str(evaluation_rule.get_failure())
            print(color.FAIL + "Evaluation failed" + color.RESET)
            print(color.FAIL + "Failure:", self.failure_msg + color.RESET)
            return False

        if original_settings:
            s.settings = original_settings
        return True


# Messages that should not print debug info
HIDDEN_MESSAGES = ['skill.converse.request', 'skill.converse.response']


class EvaluationRule(object):
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
            _x.append(['or'] +
                      [['endsWith', 'intent_type', intent_type]] +
                      [['endsWith', '__type__', intent_type]])

        # Check for adapt intent info
        if test_case.get('intent', None):
            for item in test_case['intent'].items():
                _x.append(['equal', str(item[0]), str(item[1])])

        if 'play_query_match' in test_case:
            match = test_case['play_query_match']
            print(test_case)
            phrase = match.get('phrase', test_case.get('play_query'))
            _d = ['and']
            _d.append(['equal', '__type__', 'query'])
            _d.append(['equal', 'skill_id', skill.skill_id])
            _d.append(['equal', 'phrase', phrase])
            _d.append(['gt', 'conf', match.get('confidence_threshold', 0.5)])
            self.rule.append(_d)

        # Check for expected data structure
        if test_case.get('expected_data'):
            _d = ['and']
            for item in test_case['expected_data'].items():
                _d.append(['equal', item[0], item[1]])
            self.rule.append(_d)

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
                # Check that expected dialog file is used
                if isinstance(test_case['expected_dialog'], str):
                    dialog = [test_case['expected_dialog']]  # Make list
                else:
                    dialog = test_case['expected_dialog']
                # Extract dialog texts from skill
                dialogs = []
                try:
                    for d in dialog:
                        dialogs += skill.dialog_renderer.templates[d]
                except Exception as template_load_exception:
                    print(color.FAIL +
                          "Failed to load dialog template " +
                          "'dialog/en-us/" + d + ".dialog'" +
                          color.RESET)
                    raise Exception("Can't load 'excepected_dialog': "
                                    "file '" + d + ".dialog'") \
                        from template_load_exception
                # Allow custom fields to be anything
                d = [re.sub(r'{.*?\}', r'.*', t) for t in dialogs]
                # Create rule allowing any of the sentences for that dialog
                rules = [['match', 'utterance', r] for r in d]
                self.rule.append(['or'] + rules)

        if test_case.get('changed_context', None):
            ctx = test_case['changed_context']
            if isinstance(ctx, list):
                for c in ctx:
                    self.rule.append(['equal', 'context', str(c)])
            else:
                self.rule.append(['equal', 'context', ctx])

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
