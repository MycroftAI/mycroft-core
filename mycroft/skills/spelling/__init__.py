from os.path import dirname, join

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill

__author__ = 'seanfitz'


# TODO - Localization
class SpellingSkill(MycroftSkill):
    def __init__(self):
        super(SpellingSkill, self).__init__(name="SpellingSkill")

    def initialize(self):
        self.load_vocab_files(join(dirname(__file__), 'vocab', 'en-us'))

        prefixes = ['spell', 'spell the word', 'spelling of', 'spelling of the word']
        self.__register_prefixed_regex(prefixes, "(?P<Word>\w+)")

        intent = IntentBuilder("SpellingIntent").require("SpellingKeyword").require("Word").build()
        self.register_intent(intent, self.handle_intent)

    def __register_prefixed_regex(self, prefixes, suffix_regex):
        for prefix in prefixes:
            self.register_regex(prefix + ' ' + suffix_regex)

    def handle_intent(self, message):
        word = message.metadata.get("Word")
        spelled_word = ', '.join(word).lower()
        self.speak(spelled_word)

    def stop(self):
        pass


def create_skill():
    return SpellingSkill()
