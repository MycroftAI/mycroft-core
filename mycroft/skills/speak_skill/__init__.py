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

from mycroft.skills.core import MycroftSkill

__author__ = 'jasonehines'


# TODO - Localization

class SpeakSkill(MycroftSkill):
    def __init__(self):
        super(SpeakSkill, self).__init__(name="SpeakSkill")

    def initialize(self):
        prefixes = [
            'speak', 'say', 'repeat']
        self.__register_prefixed_regex(prefixes, "(?P<Words>.*)")

        intent = IntentBuilder("SpeakIntent").require(
            "SpeakKeyword").require("Words").build()
        self.register_intent(intent, self.handle_speak_intent)

    def __register_prefixed_regex(self, prefixes, suffix_regex):
        for prefix in prefixes:
            self.register_regex(prefix + ' ' + suffix_regex)

    def handle_speak_intent(self, message):
        words = message.data.get("Words")
        self.speak(words)

    def stop(self):
        pass


def create_skill():
    return SpeakSkill()
