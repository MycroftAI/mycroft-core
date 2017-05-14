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
import time
from mycroft.messagebus.message import Message
from mycroft.skills.core import open_intent_envelope
from mycroft.util.log import getLogger
from mycroft.util.parse import normalize

__author__ = 'seanfitz'

logger = getLogger(__name__)


class IntentService(object):
    def __init__(self, emitter):
        self.engine = IntentDeterminationEngine()
        self.emitter = emitter
        self.emitter.on('register_vocab', self.handle_register_vocab)
        self.emitter.on('register_intent', self.handle_register_intent)
        self.emitter.on('recognizer_loop:utterance', self.handle_utterance)
        self.emitter.on('detach_intent', self.handle_detach_intent)
        self.emitter.on('detach_skill', self.handle_detach_skill)
        self.emitter.on('converse_status_response', self.handle_conversation_response)
        self.emitter.on('intent_request', self.handle_intent_request)
        self.emitter.on('intent_to_skill_request', self.handle_intent_to_skill_request)
        self.active_skills = []  # [skill_id , timestamp]
        self.skill_ids = {} # {skill_id: [intents]}
        self.converse_timeout = 5  # minutes to prune active_skills

    def do_conversation(self, utterances, skill_id, lang):
        self.emitter.emit(Message("converse_status_request", {
            "skill_id": skill_id, "utterances": utterances, "lang": lang}))
        self.waiting = True
        self.result = False
        while self.waiting:
            pass
        return self.result

    def handle_intent_to_skill_request(self, message):
        intent = message.data["intent_name"]
        for id in self.skill_ids:
            for name in self.skill_ids[id]:
                if name == intent:
                    self.emitter.emit(Message("intent_to_skill_response", {
                        "skill_id": id, "intent_name": intent}))
                    return id
        self.emitter.emit(Message("intent_to_skill_response", {
            "skill_id": 0, "intent_name": intent}))
        return 0

    def handle_conversation_response(self, message):
        # id = message.data["skill_id"]
        # no need to crosscheck id because waiting before new request is made
        # no other skill will make this request is safe assumption
        result = message.data["result"]
        self.result = result
        self.waiting = False

    def remove_active_skill(self, skill_id):
        for skill in self.active_skills:
            if skill[0] == skill_id:
                self.active_skills.remove(skill)

    def add_active_skill(self, skill_id):
        # you have to search the list for an existing entry that already contains it and remove that reference
        self.remove_active_skill(skill_id)
        # add skill with timestamp to start of skill_list
        self.active_skills.insert(0, [skill_id, time.time()])

    def handle_intent_request(self, message):
        utterance = message.data["utterance"]
        # Get language of the utterance
        lang = message.data.get('lang', None)
        if not lang:
            lang = "en-us"
        best_intent = None
        try:
            # normalize() changes "it's a boy" to "it is boy", etc.
            best_intent = next(self.engine.determine_intent(
                normalize(utterance, lang), 100))

            # TODO - Should Adapt handle this?
            best_intent['utterance'] = utterance
        except StopIteration, e:
            logger.exception(e)

        if best_intent and best_intent.get('confidence', 0.0) > 0.0:
            skill_id = int(best_intent['intent_type'].split(":")[0])
            intent_name = best_intent['intent_type'].split(":")[1]
            self.emitter.emit(Message("intent_response", {
                "skill_id": skill_id, "utterance": utterance, "lang": lang, "intent_name":intent_name}))
            return True
        self.emitter.emit(Message("intent_response", {
            "skill_id": 0, "utterance": utterance, "lang": lang, "intent_name": ""}))
        return False

    def handle_utterance(self, message):
        # Get language of the utterance
        lang = message.data.get('lang', None)
        if not lang:
            lang = "en-us"

        utterances = message.data.get('utterances', '')
        # check for conversation time-out
        self.active_skills = [skill for skill in self.active_skills
                              if time.time() - skill[1] <= self.converse_timeout * 60]

        # check if any skill wants to handle utterance
        for skill in self.active_skills:
            if self.do_conversation(utterances, skill[0], lang):
                # update timestamp, or there will be a timeout where
                # intent stops conversing whether its being used or not
                self.add_active_skill(skill[0])
                return
                # no skill wants to handle utterance, proceed

        best_intent = None
        for utterance in utterances:
            try:
                # normalize() changes "it's a boy" to "it is boy", etc.
                best_intent = next(self.engine.determine_intent(
                    normalize(utterance, lang), 100))

                # TODO - Should Adapt handle this?
                best_intent['utterance'] = utterance
            except StopIteration, e:
                logger.exception(e)
                continue

        if best_intent and best_intent.get('confidence', 0.0) > 0.0:
            reply = message.reply(
                best_intent.get('intent_type'), best_intent)
            self.emitter.emit(reply)
            # update active skills
            skill_id = int(best_intent['intent_type'].split(":")[0])
            self.add_active_skill(skill_id)

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
        #  map intent_name to skill_id
        skill_id = int(intent.name.split(":")[0])
        intent_name = intent.name.split(":")[1]
        if skill_id not in self.skill_ids.keys():
            self.skill_ids[skill_id] = []
        if intent_name not in self.skill_ids[skill_id]:
            self.skill_ids[skill_id].append(intent_name)

    def handle_detach_intent(self, message):
        intent_name = message.data.get('intent_name')
        new_parsers = [
            p for p in self.engine.intent_parsers if p.name != intent_name]
        self.engine.intent_parsers = new_parsers

    def handle_detach_skill(self, message):
        skill_id = message.data.get('skill_id')
        new_parsers = [
            p for p in self.engine.intent_parsers if
            not p.name.startswith(skill_id)]
        self.engine.intent_parsers = new_parsers


class IntentParser():
    def __init__(self, emitter, time_out = 20):
        self.emitter = emitter
        self.waiting = False
        self.intent = ""
        self.id = 0
        self.emitter.on("intent_response", self.handle_receive_intent)
        self.emitter.on("intent_to_skill_response", self.handle_receive_skill_id)
        self.time_out = time_out

    def determine_intent(self, utterance, lang="en-us"):
        self.waiting = True
        self.emitter.emit(Message("intent_request", {"utterance": utterance, "lang": lang}))
        start_time = time()
        t = 0
        while self.waiting and t < self.time_out:
            t = time() - start_time
        return self.intent, self.id

    def get_skill_id(self, intent_name):
        self.waiting = True
        self.id = 0
        self.emitter.emit(Message("intent_to_skill_request", {"intent_name": intent_name}))
        start_time = time()
        t = 0
        while self.waiting and t < self.time_out:
            t = time() - start_time
        self.waiting = False
        return self.id

    def handle_receive_intent(self, message):
        self.id = message.data["skill_id"]
        self.intent = message.data["intent_name"]
        self.waiting = False

    def handle_receive_skill_id(self, message):
        self.id = message.data["skill_id"]
        self.waiting = False
