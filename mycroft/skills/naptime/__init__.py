from os.path import dirname
from os.path import join

from adapt.intent import IntentBuilder
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill

__author__ = 'seanfitz'


class NapTimeSkill(MycroftSkill):
    def __init__(self):
        super(NapTimeSkill, self).__init__(name="NapTimeSkill")

    def initialize(self):
        intent_parser = IntentBuilder("NapTimeIntent").require(
            "SleepCommand").build()
        self.register_intent(intent_parser, self.handle_intent)
        self.load_vocab_files(join(dirname(__file__), 'vocab', 'en-us'))

    # TODO - Localization
    def handle_intent(self, message):
        self.emitter.emit(Message('recognizer_loop:sleep'))
        self.speak("Ok, I'm going to sleep.")

    def stop(self):
        pass


def create_skill():
    return NapTimeSkill()
