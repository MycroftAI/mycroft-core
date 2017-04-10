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

from threading import Timer
from uuid import uuid4

from adapt.intent import IntentBuilder

from mycroft.api import DeviceApi
from mycroft.identity import IdentityManager
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill


class PairingSkill(MycroftSkill):
    def __init__(self):
        super(PairingSkill, self).__init__("PairingSkill")
        self.api = DeviceApi()
        self.data = None
        self.state = str(uuid4())
        self.delay = 10
        self.activator = None

        # TODO: Add translation support
        self.nato_dict = {'A': "'A' as in Apple", 'B': "'B' as in Bravo",
                          'C': "'C' as in Charlie", 'D': "'D' as in Delta",
                          'E': "'E' as in Echo", 'F': "'F' as in Fox trot",
                          'G': "'G' as in Golf", 'H': "'H' as in Hotel",
                          'I': "'I' as in India", 'J': "'J' as in Juliet",
                          'K': "'K' as in Kilogram", 'L': "'L' as in London",
                          'M': "'M' as in Mike", 'N': "'N' as in November",
                          'O': "'O' as in Oscar", 'P': "'P' as in Paul",
                          'Q': "'Q' as in Quebec", 'R': "'R' as in Romeo",
                          'S': "'S' as in Sierra", 'T': "'T' as in Tango",
                          'U': "'U' as in Uniform", 'V': "'V' as in Victor",
                          'W': "'W' as in Whiskey", 'X': "'X' as in X-Ray",
                          'Y': "'Y' as in Yankee", 'Z': "'Z' as in Zebra",
                          '1': 'One', '2': 'Two', '3': 'Three',
                          '4': 'Four', '5': 'Five', '6': 'Six',
                          '7': 'Seven', '8': 'Eight', '9': 'Nine',
                          '0': 'Zero'}

    def initialize(self):
        intent = IntentBuilder("PairingIntent") \
            .require("PairingKeyword").require("DeviceKeyword").build()
        self.register_intent(intent, self.handle_pairing)
        self.emitter.on("mycroft.not.paired", self.not_paired)

    def not_paired(self, message):
        self.speak_dialog("pairing.not.paired")
        self.handle_pairing()

    def handle_pairing(self, message=None):
        if self.is_paired():
            self.speak_dialog("pairing.paired")
        elif self.data:
            self.speak_code()
        else:
            self.data = self.api.get_code(self.state)
            self.enclosure.deactivate_mouth_events()
            self.enclosure.mouth_text(self.data.get("code"))
            self.speak_code()
            self.__create_activator()

    def activate(self):
        try:
            token = self.data.get("token")
            login = self.api.activate(self.state, token)
            self.enclosure.activate_mouth_events()
            self.speak_dialog("pairing.paired")
            IdentityManager.save(login)
            self.emitter.emit(Message("mycroft.paired", login))
        except:
            self.data["expiration"] -= self.delay

            if self.data.get("expiration") <= 0:
                self.data = None
                self.handle_pairing()
            else:
                self.__create_activator()

    def __create_activator(self):
        self.activator = Timer(self.delay, self.activate)
        self.activator.daemon = True
        self.activator.start()

    def is_paired(self):
        try:
            device = self.api.find()
        except:
            device = None
        return device is not None

    def speak_code(self):
        code = self.data.get("code")
        self.log.info("Pairing code: " + code)
        data = {"code": '. '.join(map(self.nato_dict.get, code))}
        self.speak_dialog("pairing.code", data)

    def stop(self):
        pass

    def shutdown(self):
        super(PairingSkill, self).shutdown()
        if self.activator:
            self.activator.cancel()


def create_skill():
    return PairingSkill()
