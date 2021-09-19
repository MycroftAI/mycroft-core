# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Mycroft's intent service, providing intent parsing since forever!"""
from copy import copy
import time

from mycroft.configuration import Configuration, set_default_lf_lang
from mycroft.util.log import LOG
from mycroft.util.parse import normalize
from mycroft.metrics import report_timing, Stopwatch
from .intent_services import (
    AdaptService, AdaptIntent, FallbackService, PadatiousService, BaiduIntentMatchService, IntentMatch
)
from .intent_service_interface import open_intent_envelope


def _get_message_lang(message):
    """Get the language from the message or the default language.

    Args:
        message: message to check for language code.

    Returns:
        The languge code from the message or the default language.
    """
    default_lang = Configuration.get().get('lang', 'en-us')
    return message.data.get('lang', default_lang).lower()


def _normalize_all_utterances(utterances):
    """Create normalized versions and pair them with the original utterance.

    This will create a list of tuples with the original utterance as the
    first item and if normalizing changes the utterance the normalized version
    will be set as the second item in the tuple, if normalization doesn't
    change anything the tuple will only have the "raw" original utterance.

    Args:
        utterances (list): list of utterances to normalize

    Returns:
        list of tuples, [(original utterance, normalized) ... ]
    """
    # normalize() changes "it's a boy" to "it is a boy", etc.
    norm_utterances = [normalize(u.lower(), remove_articles=False)
                       for u in utterances]

    # Create pairs of original and normalized counterparts for each entry
    # in the input list.
    combined = []
    for utt, norm in zip(utterances, norm_utterances):
        if utt == norm:
            combined.append((utt,))
        else:
            combined.append((utt, norm))

    LOG.debug("Utterances: {}".format(combined))
    return combined


class IntentService:
    """Mycroft intent service. parses utterances using a variety of systems.

    The intent service also provides the internal API for registering and
    querying the intent service.
    """
    def __init__(self, bus):
        LOG.info('[Flow Learning] IntentService is initializing...')
        # Dictionary for translating a skill id to a name
        self.bus = bus

        self.skill_names = {}
        config = Configuration.get()
        # mycroft-core-zh:
        self.baidu_intent_match_service = None
        if True:
            self.baidu_intent_match_service = BaiduIntentMatchService(config['baidu_nlu'])
        self.adapt_service = AdaptService(config.get('context', {}))
        try:
            self.padatious_service = PadatiousService(bus, config['padatious'])
        except Exception as err:
            LOG.exception('Failed to create padatious handlers '
                          '({})'.format(repr(err)))
        self.fallback = FallbackService(bus)

        self.bus.on('register_vocab', self.handle_register_vocab)
        self.bus.on('register_intent', self.handle_register_intent)
        # mycroft-core-zh:
        self.bus.on('baidu:register_intent', self.handle_register_baidu_intent)
        self.bus.on('recognizer_loop:utterance', self.handle_utterance)
        self.bus.on('detach_intent', self.handle_detach_intent)
        self.bus.on('detach_skill', self.handle_detach_skill)
        # Context related handlers
        self.bus.on('add_context', self.handle_add_context)
        self.bus.on('remove_context', self.handle_remove_context)
        self.bus.on('clear_context', self.handle_clear_context)

        # Converse method
        self.bus.on('mycroft.speech.recognition.unknown', self.reset_converse)
        self.bus.on('mycroft.skills.loaded', self.update_skill_name_dict)

        def add_active_skill_handler(message):
            LOG.info('[Flow Learning] in add_active_skill_handler, to call add_active_skill')
            self.add_active_skill(message.data['skill_id'])

        self.bus.on('active_skill_request', add_active_skill_handler)

        # mycroft-core-zh
        def deactive_skill_handler(message):
            LOG.info(
                '[Flow Learning] in deactive_skill_handler, message.data'
                + '["skill_id"]='
                + str(message.data['skill_id']))
            deactived = self.deactive_skill(message.data['skill_id'])

            message_data = {'result': deactived}
            LOG.info(
                '[Flow Learning]'
                + ' in deactive_skill_handler to send message_data='
                + str(message_data))
            message_response = message.reply('deactive_skill_request.response',
                                             data=message_data)
            LOG.info('[Flow Learning] in deactive_skill_handler ' +
                     str(message_response))
            self.bus.emit(message_response)

        self.bus.on('deactive_skill_request', deactive_skill_handler)
        self.active_skills = []  # [skill_id , timestamp]
        self.converse_timeout = 5  # minutes to prune active_skills
        # mycroft-core-zh:
        self.deactive_skill_indicator = -1

        # Intents API
        self.registered_vocab = []
        self.bus.on('intent.service.intent.get', self.handle_get_intent)
        self.bus.on('intent.service.skills.get', self.handle_get_skills)
        self.bus.on('intent.service.active_skills.get',
                    self.handle_get_active_skills)
        self.bus.on('intent.service.adapt.get', self.handle_get_adapt)
        self.bus.on('intent.service.adapt.manifest.get',
                    self.handle_adapt_manifest)
        self.bus.on('intent.service.adapt.vocab.manifest.get',
                    self.handle_vocab_manifest)
        self.bus.on('intent.service.padatious.get',
                    self.handle_get_padatious)
        self.bus.on('intent.service.padatious.manifest.get',
                    self.handle_padatious_manifest)
        self.bus.on('intent.service.padatious.entities.manifest.get',
                    self.handle_entity_manifest)

    @property
    def registered_intents(self):
        return [parser.__dict__
                for parser in self.adapt_service.engine.intent_parsers]

    def update_skill_name_dict(self, message):
        """Messagebus handler, updates dict of id to skill name conversions."""
        self.skill_names[message.data['id']] = message.data['name']

    def get_skill_name(self, skill_id):
        """Get skill name from skill ID.

        Args:
            skill_id: a skill id as encoded in Intent handlers.

        Returns:
            (str) Skill name or the skill id if the skill wasn't found
        """
        return self.skill_names.get(skill_id, skill_id)

    def reset_converse(self, message):
        """Let skills know there was a problem with speech recognition"""
        lang = _get_message_lang(message)
        set_default_lf_lang(lang)
        for skill in copy(self.active_skills):
            self.do_converse(None, skill[0], lang, message)

    def do_converse(self, utterances, skill_id, lang, message):
        """Call skill and ask if they want to process the utterance.

        Args:
            utterances (list of tuples): utterances paired with normalized
                                         versions.
            skill_id: skill to query.
            lang (str): current language
            message (Message): message containing interaction info.
        """
        LOG.info('[Flow Learning] in do_converse, ')
        converse_msg = (message.reply("skill.converse.request", {
            "skill_id": skill_id, "utterances": utterances, "lang": lang}))
        result = self.bus.wait_for_response(converse_msg,
                                            'skill.converse.response')
        if result and 'error' in result.data:
            self.handle_converse_error(result)
            ret = False
        elif result is not None:
            ret = result.data.get('result', False)
        else:
            ret = False
        return ret

    def handle_converse_error(self, message):
        """Handle error in converse system.

        Args:
            message (Message): info about the error.
        """
        skill_id = message.data["skill_id"]
        error_msg = message.data['error']
        LOG.error("{}: {}".format(skill_id, error_msg))
        if message.data["error"] == "skill id does not exist":
            self.remove_active_skill(skill_id)

    def remove_active_skill(self, skill_id):
        """Remove a skill from being targetable by converse.

        Args:
            skill_id (str): skill to remove
        """
        LOG.info('[Flow Learning] active_skills before removal' + str(self.active_skills))
        for skill in self.active_skills:
            if skill[0] == skill_id:
                LOG.info('[Flow Learning] remove skill_id : ' + skill_id)
                self.active_skills.remove(skill)
        LOG.info('[Flow Learning] active_skills after removal' + str(self.active_skills))

    # mycroft-core-zh:
    # only deactive the skill but not remove it from the list of active_skills.
    def deactive_skill(self, skill_id):
        LOG.info('[Flow Learning] active_skills before deactive' +
                 str(self.active_skills))
        deactived = False
        for skill in self.active_skills:
            if skill[0] == skill_id:
                LOG.info('[Flow Learning] deactive skill_id : ' + skill_id)
                skill[1] = self.deactive_skill_indicator
                deactived = True
        LOG.info('[Flow Learning] active_skills after deactive' +
                 str(self.active_skills))
        return deactived

    # mycroft-core-zh:
    # The purpose is to create helper function to handle the scenario when the skill ends.
    # if skill has been deactived, then remove the skill
    # if skill is not in active_skills, then add it in by calling add_active_skill
    # if skill is active and in active_skills, then refresh it by calling add_active_skill
    def refresh_active_skill(self, skill_id):
        whetherRemoveSkill = False
        for skill in self.active_skills:
            if skill[0] == skill_id and skill[1] == self.deactive_skill_indicator:
                LOG.info('[Flow Learning] remove_skill is to be called, skill_id : ' + skill_id)
                whetherRemoveSkill = True
        if whetherRemoveSkill:
            LOG.info('[Flow Learning] in refresh_active_skill, remove_skill is to be called, skill_id : ' + skill_id)
            self.remove_active_skill(skill_id)
        else:
            LOG.info('[Flow Learning] in refresh_active_skill, add_active_skill is to be called, skill_id : ' + skill_id)
            self.add_active_skill(skill_id)

    def add_active_skill(self, skill_id):
        """Add a skill or update the position of an active skill.

        The skill is added to the front of the list, if it's already in the
        list it's removed so there is only a single entry of it.

        Args:
            skill_id (str): identifier of skill to be added.
        """
        # search the list for an existing entry that already contains it
        # and remove that reference
        LOG.info('[Flow Learning] in add_active_skill, skill_id = ' + str(skill_id))
        if skill_id != '':
            self.remove_active_skill(skill_id)
            # add skill with timestamp to start of skill_list
            self.active_skills.insert(0, [skill_id, time.time()])
        else:
            LOG.warning('Skill ID was empty, won\'t add to list of '
                        'active skills.')

    def send_metrics(self, intent, context, stopwatch):
        """Send timing metrics to the backend.

        NOTE: This only applies to those with Opt In.

        Args:
            intent (IntentMatch or None): intet match info
            context (dict): context info about the interaction
            stopwatch (StopWatch): Timing info about the skill parsing.
        """
        ident = context['ident'] if 'ident' in context else None
        # Determine what handled the intent
        if intent and intent.intent_service == 'Converse':
            intent_type = '{}:{}'.format(intent.skill_id, 'converse')
        elif intent and intent.intent_service == 'Fallback':
            intent_type = 'fallback'
        elif intent:  # Handled by an other intent parser
            # Recreate skill name from skill id
            parts = intent.intent_type.split(':')
            intent_type = self.get_skill_name(parts[0])
            if len(parts) > 1:
                intent_type = ':'.join([intent_type] + parts[1:])
        else:  # No intent was found
            intent_type = 'intent_failure'

        report_timing(ident, 'intent_service', stopwatch,
                      {'intent_type': intent_type})

    def handle_utterance(self, message):
        """Main entrypoint for handling user utterances with Mycroft skills

        Monitor the messagebus for 'recognizer_loop:utterance', typically
        generated by a spoken interaction but potentially also from a CLI
        or other method of injecting a 'user utterance' into the system.

        Utterances then work through this sequence to be handled:
        1) Active skills attempt to handle using converse()
        1.5) Baidu NLU somehow match intents -- used for mycroft-core-zh
        2) Padatious high match intents (conf > 0.95)
        3) Adapt intent handlers
        5) High Priority Fallbacks
        6) Padatious near match intents (conf > 0.8)
        7) General Fallbacks
        8) Padatious loose match intents (conf > 0.5)
        9) Catch all fallbacks including Unknown intent handler

        If all these fail the complete_intent_failure message will be sent
        and a generic info of the failure will be spoken.

        Args:
            message (Message): The messagebus data
        """
        LOG.info('[Flow Learning] in mycroft.skills.intent_service.py.IntentService.handle_utterance, try to match utterance with Mycroft skills or some handle.')
        LOG.info('[Flow Learning] in mycroft.skills.intent_service.py.IntentService.handle_utterance, active_skills = ' + str(self.active_skills))
        try:
            lang = _get_message_lang(message)
            set_default_lf_lang(lang)

            utterances = message.data.get('utterances', [])
            LOG.info('[Flow Learning] in mycroft.skills.intent_service.py.IntentService.handle_utterance, utterances= ' + str(utterances))
            combined = _normalize_all_utterances(utterances)

            stopwatch = Stopwatch()

            # List of functions to use to match the utterance with intent.
            # These are listed in priority order.
            match_funcs = [
                self._converse, self.baidu_intent_match_service.match_intent, self.padatious_service.match_high,
                self.adapt_service.match_intent, self.fallback.high_prio,
                self.padatious_service.match_medium, self.fallback.medium_prio,
                self.padatious_service.match_low, self.fallback.low_prio
            ]

            match = None
            with stopwatch:
                # Loop through the matching functions until a match is found.
                for match_func in match_funcs:
                    match = match_func(combined, lang, message)
                    if match:
                        break
            if match:
                LOG.info('[Flow Learning] A skill or handle is matched. match.skill_id = ' + str(match.skill_id) + ', match.intent_type = ' + str(match.intent_type))
                if match.skill_id:
                    LOG.info('[Flow Learning] matched and is about to add_active_skill, skill_id ==' + match.skill_id)
                    # mycroft-core-zh: change this for the scenario that skill ends.
                    self.refresh_active_skill(match.skill_id)
                    # If the service didn't report back the skill_id it
                    # takes on the responsibility of making the skill "active"

                # Launch skill if not handled by the match function
                if match.intent_type:
                    reply = message.reply(match.intent_type, match.intent_data)
                    self.bus.emit(reply)

            else:
                # Nothing was able to handle the intent
                # Ask politely for forgiveness for failing in this vital task
                LOG.info('[Flow Learning] Nothing matches, ask politely for forgiveness.')
                self.send_complete_intent_failure(message)
            self.send_metrics(match, message.context, stopwatch)
        except Exception as err:
            LOG.exception(err)

    def _converse(self, utterances, lang, message):
        """Give active skills a chance at the utterance

        Args:
            utterances (list):  list of utterances
            lang (string):      4 letter ISO language code
            message (Message):  message to use to generate reply

        Returns:
            IntentMatch if handled otherwise None.
        """
        LOG.info('[Flow learning] in intent_service.py._converse ')
        utterances = [item for tup in utterances for item in tup]
        # check for conversation time-out
        self.active_skills = [skill for skill in self.active_skills
                              if time.time() - skill[
                                  1] <= self.converse_timeout * 60]
        LOG.info('[Flow learning] in intent_service.py._converse active skills = ' + str(self.active_skills))

        # check if any skill wants to handle utterance
        for skill in copy(self.active_skills):
            LOG.info('[Flow learning] in intent_service.py._converse in loop, active skills = ' + str(skill))
            if self.do_converse(utterances, skill[0], lang, message):
                # update timestamp, or there will be a timeout where
                # intent stops conversing whether its being used or not
                return IntentMatch('Converse', None, None, skill[0])
        return None

    def send_complete_intent_failure(self, message):
        """Send a message that no skill could handle the utterance.

        Args:
            message (Message): original message to forward from
        """
        LOG.info('[Flow Learning] send message of complete_intent_failure to bus.')
        self.bus.emit(message.forward('complete_intent_failure'))

    def handle_register_vocab(self, message):
        """Register adapt vocabulary.

        Args:
            message (Message): message containing vocab info
        """
        start_concept = message.data.get('start')
        end_concept = message.data.get('end')
        regex_str = message.data.get('regex')
        alias_of = message.data.get('alias_of')
        self.adapt_service.register_vocab(start_concept, end_concept,
                                          alias_of, regex_str)
        self.registered_vocab.append(message.data)

    # mycroft-core-zh: register the intent into adapt's engine, so that engine can work.
    def handle_register_intent(self, message):
        """Register adapt intent.

        Args:
            message (Message): message containing intent info
        """
        intent = open_intent_envelope(message)
        self.adapt_service.register_intent(intent)

    # mycroft-core-zh
    def handle_register_baidu_intent(self, message):
        LOG.info('[Flow Learning] in intent_service.py handle_register_baidu_intent, no need to do anything. ')
        pass

    def handle_detach_intent(self, message):
        """Remover adapt intent.

        Args:
            message (Message): message containing intent info
        """
        intent_name = message.data.get('intent_name')
        self.adapt_service.detach_intent(intent_name)

    def handle_detach_skill(self, message):
        """Remove all intents registered for a specific skill.

        Args:
            message (Message): message containing intent info
        """
        skill_id = message.data.get('skill_id')
        self.adapt_service.detach_skill(skill_id)

    def handle_add_context(self, message):
        """Add context

        Args:
            message: data contains the 'context' item to add
                     optionally can include 'word' to be injected as
                     an alias for the context item.
        """
        entity = {'confidence': 1.0}
        context = message.data.get('context')
        word = message.data.get('word') or ''
        origin = message.data.get('origin') or ''
        # if not a string type try creating a string from it
        if not isinstance(word, str):
            word = str(word)
        entity['data'] = [(word, context)]
        entity['match'] = word
        entity['key'] = word
        entity['origin'] = origin
        self.adapt_service.context_manager.inject_context(entity)

    def handle_remove_context(self, message):
        """Remove specific context

        Args:
            message: data contains the 'context' item to remove
        """
        context = message.data.get('context')
        if context:
            self.adapt_service.context_manager.remove_context(context)

    def handle_clear_context(self, _):
        """Clears all keywords from context """
        self.adapt_service.context_manager.clear_context()

    def handle_get_intent(self, message):
        """Get intent from either adapt or padatious.

        Args:
            message (Message): message containing utterance
        """
        LOG.info('[Flow Learning] in handle_get_intent !!!!!!!!!!   intent.service.intent.get message is used!!')
        utterance = message.data["utterance"]
        lang = message.data.get("lang", "en-us")
        combined = _normalize_all_utterances([utterance])

        # List of functions to use to match the utterance with intent.
        # These are listed in priority order.
        # TODO once we have a mechanism for checking if a fallback will
        #  trigger without actually triggering it, those should be added here
        match_funcs = [
            self.padatious_service.match_high,
            self.adapt_service.match_intent,
            # self.fallback.high_prio,
            self.padatious_service.match_medium,
            # self.fallback.medium_prio,
            self.padatious_service.match_low,
            # self.fallback.low_prio
        ]
        # Loop through the matching functions until a match is found.
        for match_func in match_funcs:
            match = match_func(combined, lang, message)
            if match:
                if match.intent_type:
                    intent_data = match.intent_data
                    intent_data["intent_name"] = match.intent_type
                    intent_data["intent_service"] = match.intent_service
                    intent_data["skill_id"] = match.skill_id
                    intent_data["handler"] = match_func.__name__
                    self.bus.emit(message.reply("intent.service.intent.reply",
                                                {"intent": intent_data}))
                return

        # signal intent failure
        self.bus.emit(message.reply("intent.service.intent.reply",
                                    {"intent": None}))

    def handle_get_skills(self, message):
        """Send registered skills to caller.

        Argument:
            message: query message to reply to.
        """
        self.bus.emit(message.reply("intent.service.skills.reply",
                                    {"skills": self.skill_names}))

    def handle_get_active_skills(self, message):
        """Send active skills to caller.

        Argument:
            message: query message to reply to.
        """
        self.bus.emit(message.reply("intent.service.active_skills.reply",
                                    {"skills": self.active_skills}))

    def handle_get_adapt(self, message):
        """handler getting the adapt response for an utterance.

        Args:
            message (Message): message containing utterance
        """
        utterance = message.data["utterance"]
        lang = message.data.get("lang", "en-us")
        combined = _normalize_all_utterances([utterance])
        intent = self.adapt_service.match_intent(combined, lang)
        intent_data = intent.intent_data if intent else None
        self.bus.emit(message.reply("intent.service.adapt.reply",
                                    {"intent": intent_data}))

    def handle_adapt_manifest(self, message):
        """Send adapt intent manifest to caller.

        Argument:
            message: query message to reply to.
        """
        self.bus.emit(message.reply("intent.service.adapt.manifest",
                                    {"intents": self.registered_intents}))

    def handle_vocab_manifest(self, message):
        """Send adapt vocabulary manifest to caller.

        Argument:
            message: query message to reply to.
        """
        self.bus.emit(message.reply("intent.service.adapt.vocab.manifest",
                                    {"vocab": self.registered_vocab}))

    def handle_get_padatious(self, message):
        """messagebus handler for perfoming padatious parsing.

        Args:
            message (Message): message triggering the method
        """
        utterance = message.data["utterance"]
        norm = message.data.get('norm_utt', utterance)
        intent = self.padatious_service.calc_intent(utterance)
        if not intent and norm != utterance:
            intent = self.padatious_service.calc_intent(norm)
        if intent:
            intent = intent.__dict__
        self.bus.emit(message.reply("intent.service.padatious.reply",
                                    {"intent": intent}))

    def handle_padatious_manifest(self, message):
        """Messagebus handler returning the registered padatious intents.

        Args:
            message (Message): message triggering the method
        """
        self.bus.emit(message.reply(
            "intent.service.padatious.manifest",
            {"intents": self.padatious_service.registered_intents}))

    def handle_entity_manifest(self, message):
        """Messagebus handler returning the registered padatious entities.

        Args:
            message (Message): message triggering the method
        """
        self.bus.emit(message.reply(
            "intent.service.padatious.entities.manifest",
            {"entities": self.padatious_service.registered_entities}))
