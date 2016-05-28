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
from os.path import dirname, join

from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class StopSkill(MycroftSkill):
    def __init__(self):
        super(StopSkill, self).__init__(name="StopSkill")

    def initialize(self):
        # TODO - To be generalized in MycroftSkill
        self.load_vocab_files(join(dirname(__file__), 'vocab', self.lang))
        intent = IntentBuilder("StopIntent").require("StopKeyword").build()
        self.register_intent(intent, self.handle_intent)

    def handle_intent(self, event):
        self.emitter.emit(Message("mycroft.stop"))

    def stop(self):
        pass


def create_skill():
    return StopSkill()
