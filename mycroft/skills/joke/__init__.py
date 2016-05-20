from os.path import dirname

import pyjokes

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'crios'

LOGGER = getLogger(__name__)


class JokingSkill(MycroftSkill):
    def __init__(self):
        super(JokingSkill, self).__init__(name="JokingSkill")

    def initialize(self):
        self.load_data_files(dirname(__file__))

        intent = IntentBuilder("JokingIntent").require("JokingKeyword").build()
        self.register_intent(intent, self.handle_intent)

    def handle_intent(self, message):
        self.speak(pyjokes.get_joke(language=self.lang[:-3], category='all'))

    def stop(self):
        pass


def create_skill():
    return JokingSkill()
