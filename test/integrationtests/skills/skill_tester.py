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

import Queue
import json
import time

import os
import re
import ast
from os.path import join, isdir
from pyee import EventEmitter

from mycroft.messagebus.message import Message
from mycroft.skills.core import create_skill_descriptor, load_skill, MycroftSkill

MainModule = '__init__'

DEFAULT_EVALUAITON_TIMEOUT = 30


def get_skills(skills_folder):
    """
        Find skills in the skill folder or sub folders.
        Recursive traversal into subfolders stop when a __init__.py file
        is discovered

        Args:
            skills_folder:  Folder to start a search for skills __init__.py files
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

    skills = sorted(skills, key=lambda p: p.get('name'))
    return skills


def load_skills(emitter, skills_root):
    """
        Load all skills and set up emitter

        Args:
            emitter: The emmitter to use
            skills_root: Directory of the skills __init__.py

    """
    skill_list = []
    skill_id = 1211234556  # Use a skill id similar to the full Mycroft
    for skill in get_skills(skills_root):
        skill_list.append(load_skill(skill, emitter, skill_id))
        skill_id += 1

    return skill_list


def unload_skills(skills):
    for s in skills:
        s.shutdown()


class InterceptEmitter(object):
    """
        This class intercepts and allows emitting events between the skill_tester and
        the skill being tested.
        When a test is running emitted communication is intercepted for analysis
    """

    def __init__(self):
        self.emitter = EventEmitter()
        self.q = None

    def on(self, event, f):
        # run all events
        print "Event: " + str(event)
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


class MockSkillsLoader(object):
    """
        Load a skill and set up emitter

    """

    def __init__(self, skills_root):
        self.skills_root = skills_root
        self.emitter = InterceptEmitter()
        from mycroft.skills.intent_service import IntentService
        self.ih = IntentService(self.emitter)
        self.skills = None

    def load_skills(self):
        self.skills = load_skills(self.emitter, self.skills_root)
        self.skills = [s for s in self.skills if s]
        return self.emitter.emitter  # kick out the underlying emitter

    def unload_skills(self):
        unload_skills(self.skills)


class SkillTest(object):
    """
        This class is instantiated for each skill being tested. It holds the data
        needed for the test, and contains the methods doing the test

    """

    def __init__(self, skill, test_case_file, emitter):
        self.skill = skill
        self.test_case_file = test_case_file
        self.emitter = emitter
        self.dict = dict
        self.output_file = None
        self.returned_intent = False

    def run(self, loader):
        """
            Run a test for a skill. The skill, test_case_file and emitter is
            already set up in the __init__ method

            Args:
                loader:  A list of loaded skills
        """
        s = [s for s in loader.skills if s and s._dir == self.skill][0]
#        s = filter(lambda s: s and s._dir == self.skill, loader.skills)[0]
        print('Test case file: ' + self.test_case_file)
        test_case = json.load(open(self.test_case_file, 'r'))
        print "Test case: " + str(test_case)
        evaluation_rule = EvaluationRule(test_case)

        # Set up queue for emitted events. Because
        # the evaluation method expects events to be received in convoy,
        # and be handled one by one. We cant make assumptions about threading
        # in the core or the skill
        q = Queue.Queue()
        s.emitter.q = q

        # Set up context before calling intent
        # This option makes it possible to better isolate (reduce dependance) between test_cases
        cxt = test_case.get('remove_context', None)
        if cxt:
            if isinstance(cxt, list):
                for x in cxt:
                    MycroftSkill.remove_context(s, x)
            else:
                MycroftSkill.remove_context(s, cxt)

        cxt = test_case.get('set_context', None)
        if cxt:
            for key, value in cxt.iteritems():
                MycroftSkill.set_context(s, key, value)

        # Emit an utterance, just like the STT engine does.  This sends the
        # provided text to the skill engine for intent matching and it then
        # invokes the skill.
        self.emitter.emit(
            'recognizer_loop:utterance',
            Message('recognizer_loop:utterance',
                    {'utterances': [test_case.get('utterance', None)]}))

        # Wait up to X seconds for the test_case to complete
        timeout = time.time() + int(test_case.get('evaluation_timeout', None)) \
            if test_case.get('evaluation_timeout', None) and isinstance(test_case['evaluation_timeout'], int) \
            else time.time() + DEFAULT_EVALUAITON_TIMEOUT
        while not evaluation_rule.all_succeeded():
            try:
                event = q.get(timeout=1)
                evaluation_rule.evaluate(event.data)
            except Queue.Empty:
                pass
            if time.time() > timeout:
                break

        # TODO: Check that all intents are tested

        # Stop emmiter from sending on queue
        s.emitter.q = None

        # remove the skill which is not responding
        self.emitter.remove_all_listeners('speak')

        # Report test result if failed
        if not evaluation_rule.all_succeeded():
            print "Evaluation failed"
            print "Rule status: " + str(evaluation_rule.rule)
            assert False


# TODO: Add command line utility to test an event against a test_case, allow for debugging tests

class EvaluationRule(object):
    """
        This class initially convert the test_case json file to internal rule format, which is
        stored throughout the testcase run. All Messages on the event bus can be evaluated against the
        rules (test_case)

        This approach makes it easier to add new tests, since Message and rule traversal is already
        set up for the internal rule format.
        The test writer can use the internal rule format directly in the test_case
        using the assert keyword, which allows for more powerfull/individual
        test cases than the standard dictionaly
    """

    def __init__(self, test_case):
        """
            Convert test_case read from file to internal rule format

            Args:
                test_case:  The loaded test case
        """
        self.rule = []

        _x = ['and']
        if test_case.get('utterance', None):
            _x.append(['endsWith', 'intent_type', str(test_case['intent_type'])])

        if test_case.get('intent', None):
            for item in test_case['intent'].items():
                _x.append(['equal', str(item[0]), str(item[1])])

        if _x != ['and']:
            self.rule.append(_x)

        if test_case.get('expected_response', None):
            self.rule.append(['match', 'utterance', str(test_case['expected_response'])])

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

        print "Rule created " + str(self.rule)

    def evaluate(self, msg):
        """
            Main entry for evaluating a message against the rules.
            The rules are prepared in the __init__
            This method is usually called several times with different
            messages using the same rule set. Each call contributing
            to fulfilling all the rules

            Args:
                msg:  The message event to evaluate
        """
        print "Evaluating message: " + str(msg)
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
        """
            Evaluate the message against a part of the rules (recursive over rules)

            Args:
                rule:  A rule or a part of the rules to be broken down further
                msg:   The message event being evaluated

            Returns:
                 Bool: True if a partial evaluation succeeded
        """

        if rule[0] == 'equal':
            if self._get_field_value(rule[1], msg) != rule[2]:
                return False

        if rule[0] == 'notEqual':
            if self._get_field_value(rule[1], msg) == rule[2]:
                return False

        if rule[0] == 'endsWith':
            if not (self._get_field_value(rule[1], msg) and self._get_field_value(rule[1], msg).endswith(rule[2])):
                return False

        if rule[0] == 'match':
            if not (self._get_field_value(rule[1], msg) and re.match(rule[2], self._get_field_value(rule[1], msg))):
                return False

        if rule[0] == 'and':
            for i in rule[1:]:
                if not self._partial_evaluate(i, msg):
                    return False

        if rule[0] == 'or':
            for i in rule[1:]:
                if self._partial_evaluate(i, msg):
                    rule.append('succeeded')
                    return True
            return False

        rule.append('succeeded')
        return True

    def all_succeeded(self):
        """
            Test if all rules succeeded

            Returns:
                bool: True is all rules succeeded
        """
#        return len(filter(lambda x: x[-1] != 'succeeded', self.rule)) == 0
        return len([x for x in self.rule if x[-1] != 'succeeded']) == 0
