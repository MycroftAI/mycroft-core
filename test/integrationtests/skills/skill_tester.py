import json
from os.path import dirname
import re
from pyee import EventEmitter

from mycroft.messagebus.message import Message
from mycroft.skills.core import load_skills, unload_skills
# from test.integrationtests.skills.dialog import discover_dialog

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
        self.returned_intent = False
        self.output_file = None

    def compare_intents(self, expected, actual):
        for key in expected.keys():
            if actual.get(key, "").lower() != expected.get(key, "").lower():
                print(
                    "Expected %s: %s, Actual: %s" % (key, expected.get(key),
                                                     actual.get(key)))
                assert False

    # Emit an utterance, just like the STT engine does.  This sends the
    # provided text to the skill engine for intent matching and it then
    # invokes the skill.
    #
    def check_speech(self, message):
        print "Spoken response: " + message.data['utterance']

        def run_test(output_file, utterance):
            dialog_file = open( output_file, 'r' )
            dialog_line = [line.rstrip( '\n' ) for line in dialog_file]
            match_found = False
            for i in range( len( dialog_line ) ):
                if '{{' in dialog_line[i]:
                    replaced_dialog = re.sub( '\{\{(\S+)\}\}', '.*', dialog_line[i] )
                    m = re.match(replaced_dialog, utterance)
                    if m is not None:
                        match_found = True
                else:
                    if dialog_line[i] == utterance:
                        match_found = True

            if match_found is True:
                print "success"
            else:
                print "failure"
            dialog_file.close()

        run_test( self.output_file , message.data['utterance'])

        #print "SkillTest Ended: " + str( self.skill )

    def run(self, loader):
        #print "SkillTest Started: "+str(self.skill)
        for s in loader.skills:
            if s and s._dir == self.skill:
                name = s.name
                break
        example_json = json.load(open(self.example, 'r'))
        event = {'utterances': [example_json.get('utterance')]}
        output_file = str(example_json.get("expected_output"))
        self.output_file = output_file
        #print 'output_file: ' + self.output_file
        #print type(self.output_file)


        def compare(intent):
            self.compare_intents(example_json.get('intent'), intent.data)
            self.returned_intent = True

        self.emitter.once(name + ':' + example_json.get('intent_type'),
                          compare)

        self.emitter.once( 'speak', self.check_speech )

        self.emitter.emit(
            'recognizer_loop:utterance',
            Message('recognizer_loop:utterance', event))
        if not self.returned_intent:
            print("No intent handled")
            assert False







