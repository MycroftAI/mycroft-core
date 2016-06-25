from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

import requests
import json

__author__ = 'ChristopherRogers1991'

LOGGER = getLogger(__name__)


class PhillipsHueSkill(MycroftSkill):


    def __init__(self):
        super(PhillipsHueSkill, self).__init__(name="PhillipsHueSkill")
        self.ip = '192.168.1.5'
        self.url = 'http://' + self.ip + '/api/newdeveloper/groups/0/'

    def initialize(self):
        self.load_data_files(dirname(__file__))

        turn_off_intent = IntentBuilder("TurnOffIntent"). \
            require("TurnOffKeyword").build()
        self.register_intent(turn_off_intent, self.handle_turn_off_intent)

        turn_on_intent = IntentBuilder("TurnOnIntent"). \
            require("TurnOnKeyword").build()
        self.register_intent(turn_on_intent,
                             self.handle_turn_on_intent)

    def handle_turn_off_intent(self, message):
        requests.put(self.url + "action", data=json.dumps({"on": False, "transitiontime": 2}))
        self.speak_dialog("turn.off")

    def handle_turn_on_intent(self, message):
        requests.put(self.url + "action", data=json.dumps({"on": True, "transitiontime": 2}))
        self.speak_dialog("turn.on")

    def stop(self):
        pass

def create_skill():
    return PhillipsHueSkill()
