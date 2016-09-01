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
from uuid import uuid4

from adapt.intent import IntentBuilder
from os.path import dirname

from mycroft.api import DeviceApi
from mycroft.identity import IdentityManager
from mycroft.skills.core import MycroftSkill


class PairingSkill(MycroftSkill):
    def __init__(self):
        super(PairingSkill, self).__init__("PairingSkill")
        self.api = DeviceApi()
        self.data = None
        self.state = str(uuid4())
        self.identity = IdentityManager().get()

    def initialize(self):
        self.load_data_files(dirname(__file__))
        intent = IntentBuilder("PairingIntent") \
            .require("PairingKeyword").require("DeviceKeyword").build()
        self.register_intent(intent, self.handle_pairing)

    def handle_pairing(self, message):
        if not self.api.find():
            self.data = self.api.get_code(self.state)
            self.enclosure.deactivate_mouth_events()
            self.enclosure.mouth_text(self.data.code)
            self.speak_code()

    def speak_code(self):
        data = {"code": ', ,'.join(self.data.code)}
        self.speak_dialog("pairing.instructions", data)

    def stop(self):
        pass


def create_skill():
    return PairingSkill()
