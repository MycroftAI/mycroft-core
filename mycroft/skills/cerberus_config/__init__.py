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


from adapt.intent import IntentBuilder
from os.path import join, dirname

from mycroft.configuration import ConfigurationManager
from mycroft.identity import IdentityManager
from mycroft.skills.core import MycroftSkill


class CerberusConfigSkill(MycroftSkill):
    def __init__(self):
        super(CerberusConfigSkill, self).__init__("CerberusConfigSkill")

    def initialize(self):
        self.load_data_files(join(dirname(__file__)))
        intent = IntentBuilder("UpdateConfigurationIntent") \
            .require("UpdateConfigurationPhrase") \
            .build()
        self.register_intent(intent, self.handle_update_intent)

    def handle_update_intent(self, message):
        identity = IdentityManager.get()
        if identity.token:
            self.speak_dialog("not.paired")
        else:
            ConfigurationManager.load_remote()
            self.speak_dialog("config.updated")

    def stop(self):
        pass


def create_skill():
    return CerberusConfigSkill()
