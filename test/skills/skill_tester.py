import json
from os.path import dirname

from pyee import EventEmitter

from mycroft.messagebus.message import Message
from mycroft.skills.core import load_skills, unload_skills

__author__ = 'seanfitz'


class RegistrationOnlyEmitter(object):
    def __init__(self):
        self.emitter = EventEmitter()

    def on(self, event, f):
        if event in [
            'register_intent',
            'register_vocab',
            'recognizer_loop:utterance'
        ]:
            self.emitter.on(event, f)

    def emit(self, event, *args, **kwargs):
        event_name = event.type
        self.emitter.emit(event_name, event, *args, **kwargs)

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
        return self.emitter.emitter  # kick out the underlying emitter

    def unload_skills(self):
        unload_skills(self.skills)


class SkillTest(object):
    def __init__(self, skill, example, emitter):
        self.skill = skill
        self.example = example
        self.emitter = emitter
        self.returned_intent = False

    def compare_intents(self, expected, actual):
        for key in expected.keys():
            if actual.get(key, "").lower() != expected.get(key, "").lower():
                print(
                    "Expected %s: %s, Actual: %s" % (key, expected.get(key),
                                                     actual.get(key)))
                assert False

    def run(self, loader):
        for s in loader.skills:
            if s and s._dir == self.skill:
                name = s.name
        example_json = json.load(open(self.example, 'r'))
        event = {'utterances': [example_json.get('utterance')]}

        def compare(intent):
            self.compare_intents(example_json.get('intent'), intent.data)
            self.returned_intent = True

        self.emitter.once(name + ':' + example_json.get('intent_type'), compare)
        self.emitter.emit(
            'recognizer_loop:utterance',
            Message('recognizer_loop:utterance', event))
        if not self.returned_intent:
            print("No intent handled")
            assert False
