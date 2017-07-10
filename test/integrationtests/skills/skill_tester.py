import json
from os.path import dirname
import re
from pyee import EventEmitter

from mycroft.messagebus.message import Message
from mycroft.skills.core import load_skills, unload_skills
from test.integrationtests.skills.discover_tests import discover_tests

__author__ = 'seanfitz'


class RegistrationOnlyEmitter(object):
    def __init__(self):
        self.emitter = EventEmitter()

    def on(self, event, f):
        allow_events_to_execute = True  # this is for debugging purposes

        if allow_events_to_execute:
            # don't filter events, just run them all
            print "Event: "+str(event)
            self.emitter.on( event, f )
        else:
            # filter to just the registration events,
            # preventing them from actually executing
            if event in [
                'register_intent',
                'register_vocab',
                'recognizer_loop:utterance'
            ]:
                print "Event: " + str( event )
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
        self.skills = [s for s in self.skills if s]
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
        print "SkillTest Started: "+str(self.skill)
        for s in loader.skills:
            if s and s._dir == self.skill:
                name = s.name
                break
        example_json = json.load(open(self.example, 'r'))
        event = {'utterances': [example_json.get('utterance')]}

        def compare(intent):
            self.compare_intents(example_json.get('intent'), intent.data)
            self.returned_intent = True
        self.emitter.once(name + ':' + example_json.get('intent_type'),
                          compare)

        # Emit an utterance, just like the STT engine does.  This sends the
        # provided text to the skill engine for intent matching and it then
        # invokes the skill.
        #
        self.emitter.emit(
            'recognizer_loop:utterance',
            Message('recognizer_loop:utterance', event))
        if not self.returned_intent:
            print("No intent handled")
            assert False



        def check_speech(message):
            print "Spoken response: " + Message.data['utterance']
            self.emitter.once( 'speak', check_speech )
            print "SkillTest Ended: " + str( self.skill )
            if discover_tests.my_dict['utterance'] is not None:
                # single case
                run_test( discover_tests.my_dict )
                pass
            else:
                # multiple test case?
                for item in discover_tests.my_dict:
                    if item['utterance'] is not None:
                        run_test(item)



        def run_test(test_json):
            for test_item in test_json:
                if str( test_item ) == "expected_output":
                    dialog_file = open( test_json['expected_output'], 'r' )
                    dialog_line = [line.rstrip( '\n' ) for line in dialog_file]
                    for i in range( len( dialog_line ) ):
                        if '{{' in dialog_line[i]:
                            replaced_dialog = re.sub( '\{\{(\S+)\}\}', r'.*', dialog_line[i] )
                            compare_dialog_files( replaced_dialog )

        def compare_dialog_files(regex_file):
            re.match(regex_file,Message.data['utterance'])

