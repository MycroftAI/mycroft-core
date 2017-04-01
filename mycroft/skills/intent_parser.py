from adapt.engine import IntentDeterminationEngine
from adapt.intent import Intent
from mycroft.util.log import getLogger
from mycroft.messagebus.message import Message
from mycroft.util.parse import normalize

__author__ = 'jarbas'

logger = getLogger(__name__)


class IntentParser():
    def __init__(self, emitter):
        self.engine = IntentDeterminationEngine()
        self.emitter = emitter
        self.reply = None
        self.emitter.on('register_vocab', self.handle_register_vocab)
        self.emitter.on('detach_intent', self.handle_detach_intent)

    def register_intent(self, intent_dict, handler=None):

        intent = Intent(intent_dict.get('name'),
                      intent_dict.get('requires'),
                      intent_dict.get('at_least_one'),
                      intent_dict.get('optional'))
        self.engine.register_intent_parser(intent)

        def receive_handler(message):
            try:
                handler(message)
            except:
                # TODO: Localize
                logger.error(
                    "An error occurred while processing a request in IntentParser", exc_info=True)

        if handler is not None:
            self.emitter.on(intent_dict.get('name'), receive_handler)

    def determine_intent(self, utterances, lang="en-us"):
        best_intent = None
        self.reply = None
        for utterance in utterances:
            try:
                # normalize() changes "it's a boy" to "it is boy", etc.
                best_intent = next(self.engine.determine_intent(
                    normalize(utterance, lang), 100))

                # TODO - Should Adapt handle this?
                best_intent['utterance'] = utterance
            except StopIteration, e:
                logger.exception(e)
                continue
        if best_intent and best_intent.get('confidence', 0.0) > 0.0:
            self.reply = Message(best_intent.get('intent_type'), best_intent)
            return True, best_intent

        return False, best_intent

    def execute_intent(self, intent=None):
        if intent and intent.get('confidence', 0.0) > 0.0:
            self.reply = Message(intent.get('intent_type'), intent)

        if self.reply is not None:
            self.emitter.emit(self.reply)
            # self.reply = None #actually its nice to be able to call execute_intent as many times as wanted
            return True
        return False
