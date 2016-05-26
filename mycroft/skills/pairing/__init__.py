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

from threading import Thread

from adapt.intent import IntentBuilder
from os.path import dirname

from mycroft.pairing.client import DevicePairingClient
from mycroft.skills.core import MycroftSkill


class PairingSkill(MycroftSkill):
    def __init__(self):
        super(PairingSkill, self).__init__(name="PairingSkill")
        self.client = None

    def initialize(self):
        intent = IntentBuilder("PairingIntent").require(
                "DevicePairingPhrase").build()
        self.load_data_files(dirname(__file__))
        self.register_intent(intent, handler=self.handle_pairing_request)

    def handle_pairing_request(self, message):
        if not self.client:
            self.client = DevicePairingClient()
            Thread(target=self.client.run).start()
            self.emitter.on("recognizer_loop:audio_output_end",
                            self.display_pairing_code)
        self.speak_dialog(
                "pairing.instructions",
                data={"pairing_code": ', ,'.join(self.client.pairing_code)})

    def display_pairing_code(self, event=None):
        self.enclosure.mouth_text(
                "Pairing code is: " + self.client.pairing_code)

        if self.client.paired:
            self.client = None
            self.emitter.remove("recognizer_loop:audio_output_end",
                                self.display_pairing_code)

    def stop(self):
        pass


def create_skill():
    return PairingSkill()
