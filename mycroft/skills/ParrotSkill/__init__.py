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
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger


__author__ = 'jarbas'

logger = getLogger(__name__)


class ParrotSkill(MycroftSkill):

    def __init__(self):
        super(ParrotSkill, self).__init__(name="ParrotSkill")
        self.parroting = False

    def initialize(self):

        start_parrot_intent = IntentBuilder("StartParrotIntent")\
            .require("StartParrotKeyword").build()

        self.register_intent(start_parrot_intent,
                             self.handle_start_parrot_intent)

    def handle_start_parrot_intent(self, message):
        self.parroting = True
        self.speak("Parrot Mode Started")

    def stop(self):
        pass

    def Converse(self, transcript, lang="en-us"):
        if self.parroting:
            self.speak(transcript[0])
            if "stop" in transcript[0].lower():
                self.parroting = False
                self.speak("Parrot Mode Stopped")
            return True
        else:
            return False


def create_skill():
    return ParrotSkill()


