from os.path import dirname, join

from netifaces import interfaces, ifaddresses, AF_INET

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill

__author__ = 'ryanleesipes'


class IPSkill(MycroftSkill):
    def __init__(self):
        super(IPSkill, self).__init__(name="IPSkill")

    def initialize(self):
        self.load_vocab_files(join(dirname(__file__), 'vocab', 'en-us'))

        intent = IntentBuilder("IPIntent").require("IPCommand").build()
        self.register_intent(intent, self.handle_intent)

    def handle_intent(self, message):
        self.speak("Here are my available I.P. addresses.")
        for ifaceName in interfaces():
            addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr': 'No IP addr'}])]
            if ifaceName != "lo":
                self.speak('%s: %s' % ("interface: " + ifaceName + ", I.P. Address ", ', '.join(addresses)))
        self.speak("Those are all my I.P. addresses.")

    def stop(self):
        pass


def create_skill():
    return IPSkill()
