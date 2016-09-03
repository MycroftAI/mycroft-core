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
        self.delay = 10
        self.activator = None
        self.identity = IdentityManager().get()

    def initialize(self):
        self.load_data_files(dirname(__file__))
        intent = IntentBuilder("PairingIntent") \
            .require("PairingKeyword").require("DeviceKeyword").build()
        self.register_intent(intent, self.handle_pairing)

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
            self.activator = Timer(self.delay, self.activate)
            self.activator.start()

    def activate(self):
        try:
            self.api.activate(self.state, self.data.get("token"))
            self.speak_dialog("pairing.paired")
        except:
            self.data["expiration"] -= self.delay

            if self.data.get("expiration") <= 0:
                self.data = None
                self.handle_pairing()
            else:
                self.activator = Timer(self.delay, self.activate)

    def is_paired(self):
        try:
            device = self.api.find()
        except:
            device = None
        return device is not None

    def speak_code(self):
        data = {"code": '. '.join(self.data.get("code"))}
        self.speak_dialog("pairing.code", data)

    def stop(self):
        pass


def create_skill():
    return PairingSkill()
