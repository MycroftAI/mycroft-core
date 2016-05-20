from adapt.engine import IntentDeterminationEngine
from mycroft.messagebus.message import Message
from mycroft.skills.core import open_intent_envelope, MycroftSkill

__author__ = 'seanfitz'


class IntentSkill(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self, name="IntentSkill")
        self.engine = IntentDeterminationEngine()

    def initialize(self):
        self.emitter.on('register_vocab', self.handle_register_vocab)
        self.emitter.on('register_intent', self.handle_register_intent)
        self.emitter.on('recognizer_loop:utterance', self.handle_utterance)
        self.emitter.on('detach_intent', self.handle_detach_intent)

    def handle_utterance(self, message):
        utterances = message.metadata.get('utterances', '')

        best_intent = None
        for utterance in utterances:
            try:
                best_intent = next(self.engine.determine_intent(
                    utterance, num_results=100))
                # TODO - Should Adapt handle this?
                best_intent['utterance'] = utterance
            except StopIteration, e:
                continue

        if best_intent and best_intent.get('confidence', 0.0) > 0.0:
            reply = message.reply(
                best_intent.get('intent_type'), metadata=best_intent)
            self.emitter.emit(reply)
        elif len(utterances) == 1:
            self.emitter.emit(
                Message("intent_failure",
                        metadata={"utterance": utterances[0]}))
        else:
            self.emitter.emit(
                Message("multi_utterance_intent_failure",
                        metadata={"utterances": utterances}))

    def handle_register_vocab(self, message):
        start_concept = message.metadata.get('start')
        end_concept = message.metadata.get('end')
        regex_str = message.metadata.get('regex')
        alias_of = message.metadata.get('alias_of')
        if regex_str:
            self.engine.register_regex_entity(regex_str)
        else:
            self.engine.register_entity(
                start_concept, end_concept, alias_of=alias_of)

    def handle_register_intent(self, message):
        intent = open_intent_envelope(message)
        self.engine.register_intent_parser(intent)

    def handle_detach_intent(self, message):
        intent_name = message.metadata.get('intent_name')
        new_parsers = [
            p for p in self.engine.intent_parsers if p.name != intent_name]
        self.engine.intent_parsers = new_parsers

    def stop(self):
        pass


def create_skill():
    return IntentSkill()
