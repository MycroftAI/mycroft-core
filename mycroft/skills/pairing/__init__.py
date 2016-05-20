import threading

from adapt.intent import IntentBuilder
from os.path import dirname

from mycroft.pairing.client import DevicePairingClient
from mycroft.skills.core import MycroftSkill


class PairingSkill(MycroftSkill):
    def __init__(self):
        super(PairingSkill, self).__init__(name="PairingSkill")

    def initialize(self):
        intent = IntentBuilder("PairingIntent").require("DevicePairingPhrase").build()
        self.load_data_files(dirname(__file__))
        self.register_intent(intent, handler=self.handle_pairing_request)

    def handle_pairing_request(self, message):
        pairing_client = DevicePairingClient()
        pairing_code = pairing_client.pairing_code
        threading.Thread(target=pairing_client.run).start()
        self.enclosure.mouth_text("Pairing code is: " + pairing_code)
        self.speak_dialog("pairing.instructions", data={"pairing_code": ', ,'.join(pairing_code)})


    def stop(self):
        pass


def create_skill():
    return PairingSkill()
