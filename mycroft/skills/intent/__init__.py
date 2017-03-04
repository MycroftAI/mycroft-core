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


from adapt.engine import IntentDeterminationEngine

from mycroft.messagebus.message import Message
from mycroft.skills.core import open_intent_envelope, MycroftSkill
from mycroft.util.log import getLogger

import time

from mycroft.skills.main import doConversation

__author__ = 'seanfitz'

logger = getLogger(__name__)


class IntentSkill(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self, name="IntentSkill")
        self.engine = IntentDeterminationEngine()
        #### converse
        self.skills_5min = {}  # name:timestamp
        self.intent_to_skill = {}  # intent:source_skill

    def initialize(self):
        self.emitter.on('register_vocab', self.handle_register_vocab)
        self.emitter.on('register_intent', self.handle_register_intent)
        self.emitter.on('recognizer_loop:utterance', self.handle_utterance)
        self.emitter.on('detach_intent', self.handle_detach_intent)

    def handle_utterance(self, message):
        '''

        a)
        Track recently invoked skills.  This would be a list of the Skills associated with the best_intent that comes out of Adapt.
        Whenever a Skill's intent is invoked, it gets moved/placed at the top of the list.
        This list also gets curated to remove Skills that haven't been invoked in longer than, say 5 minutes.

        b)
        Before going through the current code that figures out best_intent, loop through the Skills in this list
        and call skill.Converse(utterance).  If one returns True, then they have handled the utterance
        and there is no need to do further intent processing or fallback.

        '''

        utterances = message.data.get('utterances', '')

        ##### loop trough last 5 min skills
        for skill in self.skills_5min:
            print skill
            ##### prune last_5mins_intent_dict
            print str((time.time()- self.skills_5min[skill]) / 60) + " mins ago"
            if time.time() - self.skills_5min[skill] >= 5 * 60:  # TODO make configurable?
                self.skills_5min.pop(skill, None)
            #### call skills in 5minlist skill.Converse(utterance)
            if doConversation(skill, utterances):
                ##### skill list always empty
                ##### how to execute skill.Converse method?
                return
        #### no skill wants to handle utterance, proceed

        best_intent = None
        for utterance in utterances:
            try:
                best_intent = next(self.engine.determine_intent(
                    utterance, 100))
                # TODO - Should Adapt handle this?
                best_intent['utterance'] = utterance
            except StopIteration, e:
                logger.exception(e)
                continue

        if best_intent and best_intent.get('confidence', 0.0) > 0.0:
            reply = message.reply(
                best_intent.get('intent_type'), best_intent)
            self.emitter.emit(reply)
            #### best intent detected -> update called skills dict
            name = self.intent_to_skill[best_intent['intent_type']]
            try:
                self.skills_5min[name] = time.time()
            except:
                self.skills_5min.setdefault(name, time.time())
            ###############
        elif len(utterances) == 1:
            self.emitter.emit(Message("intent_failure", {
                "utterance": utterances[0]
            }))
        else:
            self.emitter.emit(Message("multi_utterance_intent_failure", {
                "utterances": utterances
            }))

    def handle_register_vocab(self, message):
        start_concept = message.data.get('start')
        end_concept = message.data.get('end')
        regex_str = message.data.get('regex')
        alias_of = message.data.get('alias_of')
        if regex_str:
            self.engine.register_regex_entity(regex_str)
        else:
            self.engine.register_entity(
                start_concept, end_concept, alias_of=alias_of)

    def handle_register_intent(self, message):
        intent = open_intent_envelope(message)
        self.engine.register_intent_parser(intent)
        # map intent to source skill
        self.intent_to_skill.setdefault(intent.name, message.data["source_skill"])

    def handle_detach_intent(self, message):
        intent_name = message.data.get('intent_name')
        new_parsers = [
            p for p in self.engine.intent_parsers if p.name != intent_name]
        self.engine.intent_parsers = new_parsers

    def stop(self):
        pass


def create_skill():
    return IntentSkill()
