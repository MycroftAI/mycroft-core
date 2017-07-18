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


import time

from adapt.engine import IntentDeterminationEngine

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
        self.emitter.on('intent_request', self.handle_intent_request)
        self.emitter.on('intent_to_skill_request', self.handle_intent_to_skill_request)
        self.skills = {}

    def get_intent(self, utterance=None, lang="en-us"):
        best_intent = None
        if utterance:
            try:
                # normalize() changes "it's a boy" to "it is boy", etc.
                best_intent = next(self.engine.determine_intent(
                    normalize(utterance, lang), 100))

                # TODO - Should Adapt handle this?
                best_intent['utterance'] = utterance
            except StopIteration, e:
                logger.exception(e)
            except:
                logger.error("No utterance provided")
        return best_intent

    def handle_intent_request(self, message):
        utterance = message.data.get("utterance", None)
        # Get language of the utterance
        lang = message.data.get('lang', None)
        if not lang:
            lang = "en-us"
        best_intent = self.get_intent(utterance, lang)
        if best_intent and best_intent.get('confidence', 0.0) > 0.0:
            skill_name = best_intent['intent_type'].split(":")[0]
            intent_name = best_intent['intent_type'].split(":")[1]

        self.emitter.emit(Message("intent_response", {
            "skill_name": skill_name, "utterance": utterance, "lang": lang, "intent_name": intent_name}))

    def handle_intent_to_skill_request(self, message):
        # tell which skills this intent belongs to
        intent = message.data.get("intent_name")
        # list of skills because intent may be shared
        skills = []
        for skill_name in self.skills.keys():
            for intent_list in self.skills[skill_name]:
                for intent_name in intent_list:
                    if intent_name == intent:
                        skills.append(skill_name)
        self.emitter.emit(Message("intent_to_skill_response", {
            "skills": skills, "intent_name": intent}))

    def handle_utterance(self, message):
        # Get language of the utterance
        lang = message.data.get('lang', None)
        if not lang:
            lang = "en-us"

        utterances = message.data.get('utterances', '')

        best_intent = None
        for utterance in utterances:
            best_intent = self.get_intent(utterance, lang)

        if best_intent and best_intent.get('confidence', 0.0) > 0.0:
            reply = message.reply(
                best_intent.get('intent_type'), best_intent)
            self.emitter.emit(reply)
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
        #  map intent_name to source skill
        skill_name = intent.name.split(":")[0]
        intent_name = intent.name.split(":")[1]
        if skill_name not in self.skills.keys():
            self.skills[skill_name] = []
        if intent_name not in self.skills[skill_name]:
            self.skills[skill_name].append(intent_name)

    def handle_detach_intent(self, message):
        intent_name = message.data.get('intent_name')
        new_parsers = [
            p for p in self.engine.intent_parsers if p.name != intent_name]
        self.engine.intent_parsers = new_parsers

    def handle_detach_skill(self, message):
        skill_name = message.data.get('skill_name')
        new_parsers = [
            p for p in self.engine.intent_parsers if
            not p.name.startswith(skill_name)]
        self.engine.intent_parsers = new_parsers
        self.skills.pop(skill_name)


class IntentParser():
    def __init__(self, emitter, time_out=5):
        self.emitter = emitter
        self.waiting = False
        self.intent = None
        self.skill = None
        self.skills = None
        self.emitter.on("intent_response", self.handle_receive_intent)
        self.emitter.on("intent_to_skill_response", self.handle_receive_skills)
        self.time_out = time_out

    def wait(self, time_out):
        start_time = time.time()
        t = 0
        self.intent = None
        self.skill = None
        self.skills = None
        self.waiting = True
        while self.waiting and t < time_out:
            t = time.time() - start_time
            time.sleep(0.1)
        return self.waiting

    def get_intent(self, utterance, lang="en-us"):
        # return the intent this utterance will trigger
        self.emitter.emit(Message("intent_request", {"utterance": utterance, "lang": lang}))
        self.wait(self.time_out)
        return self.intent

    def get_skill_from_utterance(self, utterance, lang="en-us"):
        # return the skill this utterance will trigger
        self.emitter.emit(Message("intent_request", {"utterance": utterance, "lang": lang}))
        self.wait(self.time_out)
        return self.skill

    def get_skill_from_intent(self, intent_name):
        # return a list of skills containing this intent
        self.emitter.emit(Message("intent_to_skill_request", {"intent_name": intent_name}))
        self.wait(self.time_out)
        return self.skills

    def handle_receive_intent(self, message):
        self.skill = message.data.get("skill_name", None)
        self.intent = message.data.get("intent_name", None)
        self.waiting = False

    def handle_receive_skills(self, message):
        self.skills = message.data.get("skills")
        self.waiting = False
