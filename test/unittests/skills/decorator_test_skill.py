from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler, intent_file_handler
from adapt.intent import IntentBuilder


class TestSkill(MycroftSkill):
    """ Test skill for intent_handler decorator. """
    @intent_handler(IntentBuilder('a').require('Keyword').build())
    def handler(self, message):
        pass

    @intent_file_handler('test.intent')
    def handler2(self, message):
        pass

    def stop(self):
        pass
