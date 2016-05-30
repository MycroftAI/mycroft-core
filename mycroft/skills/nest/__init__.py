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


from os.path import dirname
import subprocess
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'crios'

LOGGER = getLogger(__name__)


class NestSkill(MycroftSkill):
    def __init__(self):
        super(NestSkill, self).__init__(name="NestSkill")

    def initialize(self):
        self.load_data_files(dirname(__file__))

        cold_intent = IntentBuilder("TooColdIntent").require("tooColdKeyword").build()
        self.register_intent(cold_intent, self.handle_too_cold_intent)

        hot_intent = IntentBuilder("TooHotIntent").require("tooHotKeyword").build()
        self.register_intent(hot_intent, self.handle_too_hot_intent)
    
    def handle_too_cold_intent(self, message):
        try:
            subprocess.call("nest --user 'username' --password 'password' temp 75", shell=False)
            self.speak_dialog('too.cold')
        except Exception as e:
                LOGGER.error("Error: {0}".format(e))

    def handle_too_hot_intent(self, message):
        try:
            subprocess.call("nest --user 'username' --password 'password' temp 68", shell=False)
            self.speak_dialog('too.hot')
        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def stop(self):
        pass


def create_skill():
    return NestSkill()
