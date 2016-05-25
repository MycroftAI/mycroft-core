# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

import threading

from adapt.intent import IntentBuilder
from os.path import dirname

from mycroft.pairing.client import DevicePairingClient
from mycroft.skills.core import MycroftSkill


class PairingSkill(MycroftSkill):
    def __init__(self):
        super(PairingSkill, self).__init__(name="PairingSkill")

    def initialize(self):
        intent = IntentBuilder("PairingIntent").require(
                "DevicePairingPhrase").build()
        self.load_data_files(dirname(__file__))
        self.register_intent(intent, handler=self.handle_pairing_request)

    def handle_pairing_request(self, message):
        pairing_client = DevicePairingClient()
        pairing_code = pairing_client.pairing_code
        threading.Thread(target=pairing_client.run).start()
        self.speak_dialog(
                "pairing.instructions",
                data={"pairing_code": ', ,'.join(pairing_code)})
        self.enclosure.mouth_text("Pairing code is: " + pairing_code)

    def stop(self):
        pass


def create_skill():
    return PairingSkill()
