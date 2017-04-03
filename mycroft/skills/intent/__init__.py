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

from mycroft.messagebus.message import Message
from mycroft.skills.core import open_intent_envelope, MycroftSkill
from mycroft.util.log import getLogger
from mycroft.util.parse import normalize

from mycroft.skills.intent_parser import IntentParser

__author__ = 'seanfitz'

logger = getLogger(__name__)


class IntentSkill(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self, name="IntentSkill")
        self.reload_skill = False

    def initialize(self):
        self.intent_parser = IntentParser(self.emitter)
        self.emitter.on('register_intent', self.handle_register_intent)
        self.emitter.on('recognizer_loop:utterance', self.handle_utterance)

    def handle_utterance(self, message):
        # Get language of the utterance
        lang = message.data.get('lang', None)
        if not lang:
            lang = "en-us"

        utterances = message.data.get('utterances', '')

        best_intent = None
        success = False

        try:
            success, best_intent = self.intent_parser.determine_intent(utterances, lang)
        except:
            logger.error("Could not determine best intent")

        if success:
            self.intent_parser.execute_intent()
        elif len(utterances) == 1:
            self.emitter.emit(Message("intent_failure", {
                "utterance": utterances[0],
                "lang": lang
            }))
        else:
            self.emitter.emit(Message("multi_utterance_intent_failure", {
                "utterances": utterances,
                "lang": lang
            }))

    def handle_register_intent(self, message):
        intent = message.data
        self.intent_parser.register_intent(intent)

    def stop(self):
        pass


def create_skill():
    return IntentSkill()
