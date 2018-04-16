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
import json
from time import sleep

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
        s._shutdown()


class RegistrationOnlyEmitter(object):
    def __init__(self):
        self.emitter = EventEmitter()

    def on(self, event, f):
        allow_events_to_execute = True

        if allow_events_to_execute:
            # don't filter events, just run them all
            print "Event: "+str(event)
            self.emitter.on(event, f)
        else:
            # filter to just the registration events,
            # preventing them from actually executing
            if event in [
                'register_intent',
                'register_vocab',
                'recognizer_loop:utterance'
            ]:
                print "Event: " + str(event)
                self.emitter.on(event, f)

    def emit(self, event, *args, **kwargs):
        event_name = event.type
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

    def load_skills(self):
        self.skills = load_skills(self.emitter, self.skills_root)
        self.skills = [s for s in self.skills if s]
        return self.emitter.emitter  # kick out the underlying emitter

    def unload_skills(self):
        unload_skills(self.skills)


class SkillTest(object):
    def __init__(self, skill, example, emitter):
        self.skill = skill
        self.example = example
        self.emitter = emitter
        self.dict = dict
        self.output_file = None
        self.returned_intent = False

    def compare_intents(self, expected, actual):
        for key in expected.keys():
            if actual.get(key, "").lower() != expected.get(key, "").lower():
                print(
                    "Expected %s: %s, Actual: %s" % (key, expected.get(key),
                                                     actual.get(key)))
                assert False

    def check_speech(self, message):
        print "Spoken response: " + message.data['utterance']
        # Comparing the expected output and actual spoken response

        def run_test(output_file, utterance):
            dialog_file = open(output_file, 'r')
            dialog_line = [line.rstrip('\n') for line in dialog_file]
            match_found = False
            for i in range(len(dialog_line)):
                if '{{' in dialog_line[i]:
                    replaced_dialog = re.sub('\{\{(\S+)\}\}',
                                             '.*', dialog_line[i])
                    m = re.match(replaced_dialog, utterance)
                    if m is not None:
                        match_found = True
                else:
                    if dialog_line[i] == utterance:
                        match_found = True

            if match_found is True:
                assert True

            else:
                assert False

            dialog_file.close()
        run_test(self.output_file, message.data['utterance'])

    def run(self, loader):
        for s in loader.skills:
            if s and s._dir == self.skill:
                name = s.name
                break
        print('file: ' + self.example)
        example_json = json.load(open(self.example, 'r'))
        event = {'utterances': [example_json.get('utterance')]}
        # Extracting the expected output from json file
        if "expected_output" in example_json:
            output_file = str(example_json.get("expected_output"))
            self.output_file = output_file
            self.emitter.once('speak', self.check_speech)
        else:
            pass

        def compare(intent):
            self.compare_intents(example_json.get('intent'), intent.data)
            self.returned_intent = True

        self.emitter.once(name + ':' + example_json.get('intent_type'),
                          compare)

        # Emit an utterance, just like the STT engine does.  This sends the
        # provided text to the skill engine for intent matching and it then
        # invokes the skill.

        self.emitter.emit(
            'recognizer_loop:utterance',
            Message('recognizer_loop:utterance', event))

        sleep(0.2)  # wait for 0.2 seconds
        # remove the skill which is not responding
        self.emitter.remove_all_listeners('speak')
        if not self.returned_intent:
            print("No intent handled")
            assert False
