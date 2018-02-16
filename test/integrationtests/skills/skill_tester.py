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
from os.path import join, isdir
from pyee import EventEmitter

from mycroft.messagebus.message import Message
from mycroft.skills.core import create_skill_descriptor, load_skill

MainModule = '__init__'


def get_skills(skills_folder):
    skills = []
    possible_skills = os.listdir(skills_folder)
    for i in possible_skills:
        location = join(skills_folder, i)
        if (isdir(location) and
                not MainModule + ".py" in os.listdir(location)):
            for j in os.listdir(location):
                name = join(location, j)
                if (not isdir(name) or
                        not MainModule + ".py" in os.listdir(name)):
                    continue
                skills.append(create_skill_descriptor(name))
        if (not isdir(location) or
                not MainModule + ".py" in os.listdir(location)):
            continue

        skills.append(create_skill_descriptor(location))
    skills = sorted(skills, key=lambda p: p.get('name'))
    return skills


def load_skills(emitter, skills_root):
    skill_list = []
    skill_id = 0
    for skill in get_skills(skills_root):
        skill_list.append(load_skill(skill, emitter, skill_id))
        skill_id += 1

    return skill_list


def unload_skills(skills):
    for s in skills:
        s.shutdown()


class RegistrationOnlyEmitter(object):
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
    def __init__(self, skills_root):
        self.skills_root = skills_root
        self.emitter = RegistrationOnlyEmitter()
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
    def __init__(self, skill, test_case_file, emitter):
        self.skill = skill
        self.test_case_file = test_case_file
        self.emitter = emitter
        self.dict = dict
        self.output_file = None
        self.returned_intent = False

    def run(self, loader):
        s = filter(lambda s: s and s._dir == self.skill, loader.skills)[0]
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

        event = {'utterances': [test_case.get('utterance')]}

        # Emit an utterance, just like the STT engine does.  This sends the
        # provided text to the skill engine for intent matching and it then
        # invokes the skill.
        # TODO: Pass something to intent, that tells that this is a test run. The skill intent can then avoid side effects
        self.emitter.emit(
            'recognizer_loop:utterance',
            Message('recognizer_loop:utterance', event))

        # Wait up to 30 seconds for the test_case to complete (
        # TODO: add optional timeout parameter to test_case
        timeout = time.time() + 30
        while not evaluation_rule.all_succeeded():
            try:
                event = q.get(timeout=1)
            except Queue.Empty:
                pass
            evaluation_rule.evaluate(event.data)
            if time.time() > timeout:
                break

        # TODO: Check that all intents are checked (what about context)

        # Stop emmiter from sending on queue
        s.emitter.q = None

        # remove the skill which is not responding
        self.emitter.remove_all_listeners('speak')

        if not evaluation_rule.all_succeeded():
            print "Evaluation failed"
            print "Rule status: " + str(evaluation_rule.rule)
            assert False


# TODO: Add command line utility to test an event against a test_case, allow for debugging tests
class EvaluationRule(object):
    def __init__(self, test_case):
        # Convert test case to internal rule format
        # TODO: Add support for expected response, and others
        self.rule = []

        _x = ['and']
        if test_case.get('utterance', None):
            _x.append(['endsWith', 'intent_type', str(test_case['intent_type'])])

        if test_case.get('intent', None):
            for item in test_case['intent'].items():
                _x.append(['equal', str(item[0]), str(item[1])])

        if _x != ['and']:
            self.rule.append(_x)

        if test_case.get('assert', None):
            for _x in eval(test_case['assert']):
                self.rule.append(_x)

        print "Rule created " + str(self.rule)

    def get_field_value(self, rule, msg):
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

    def evaluate(self, msg):
        print "Evaluating message: " + str(msg)
        for r in self.rule:
            self.partial_evaluate(r, msg)

    def partial_evaluate(self, rule, msg):
        if rule[0] == 'equal':
            if self.get_field_value(rule[1], msg) != rule[2]:
                return False

        if rule[0] == 'notEqual':
            if self.get_field_value(rule[1], msg) == rule[2]:
                return False

        if rule[0] == 'endsWith':
            if not (self.get_field_value(rule[1], msg) and self.get_field_value(rule[1], msg).endswith(rule[2])):
                return False

        if rule[0] == 'match':
            if not (self.get_field_value(rule[1], msg) and re.match(rule[2], self.get_field_value(rule[1], msg))):
                return False

        if rule[0] == 'and':
            for i in rule[1:]:
                if not self.partial_evaluate(i, msg):
                    return False

        if rule[0] == 'or':
            for i in rule[1:]:
                if self.partial_evaluate(i, msg):
                    rule.append('succeeded')
                    return True
            return False

        rule.append('succeeded')
        return True

    def all_succeeded(self):
        return len(filter(lambda x: x[-1] != 'succeeded', self.rule)) == 0
