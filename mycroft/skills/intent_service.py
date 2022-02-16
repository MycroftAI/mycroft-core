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
from mycroft.configuration import Configuration, setup_locale
from mycroft.messagebus.message import Message, dig_for_message
from mycroft.metrics import report_timing, Stopwatch
from mycroft.skills.intent_service_interface import open_intent_envelope
from mycroft.skills.intent_services import (
    AdaptService, FallbackService,
    PadatiousService, PadatiousMatcher,
    ConverseService, IntentMatch
)
from mycroft.skills.permissions import ConverseMode, ConverseActivationMode
from mycroft.util.log import LOG
from mycroft.util.parse import normalize


def _get_message_lang(message=None):
    """Get the language from the message or the default language.

    Args:
        message: message to check for language code.

    Returns:
        The language code from the message or the default language.
    """
    message = message or dig_for_message()
    # TODO read active locale from LF instead
    default_lang = Configuration.get().get('lang', 'en-us')
    if not message:
        return default_lang
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
        self.bus = bus
        config = Configuration.get()

        # Dictionary for translating a skill id to a name
        self.skill_names = {}
        self.adapt_service = AdaptService(config.get('context', {}))
        try:
            self.padatious_service = PadatiousService(bus, config['padatious'])
        except Exception as err:
            LOG.exception(f'Failed to create padatious handlers ({err})')
        self.fallback = FallbackService(bus)
        self.converse = ConverseService(bus)

        self.bus.on('register_vocab', self.handle_register_vocab)
        self.bus.on('register_intent', self.handle_register_intent)
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

        self.bus.on('intent.service.skills.activate',
                    self.handle_activate_skill_request)
        self.bus.on('intent.service.skills.deactivate',
                    self.handle_deactivate_skill_request)
        # TODO backwards compat, deprecate
        self.bus.on('active_skill_request', self.handle_activate_skill_request)

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
        lang = _get_message_lang()
        return [parser.__dict__
                for parser in self.adapt_service.engines[lang].intent_parsers]

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

    # converse handling
    @property
    def active_skills(self):
        return self.converse.active_skills  # [skill_id , timestamp]

    def handle_activate_skill_request(self, message):
        # TODO imperfect solution - only a skill can activate itself
        # someone can forge this message and emit it raw, but in OpenVoiceOS all
        # skill messages should have skill_id in context, so let's make sure
        # this doesnt happen accidentally at very least
        skill_id = message.data['skill_id']
        source_skill = message.context.get("skill_id")
        self.converse.activate_skill(skill_id, source_skill)

    def handle_deactivate_skill_request(self, message):
        # TODO imperfect solution - only a skill can deactivate itself
        # someone can forge this message and emit it raw, but in ovos-core all
        # skill message should have skill_id in context, so let's make sure
        # this doesnt happen accidentally
        skill_id = message.data['skill_id']
        source_skill = message.context.get("skill_id") or skill_id
        self.converse.deactivate_skill(skill_id, source_skill)

    def reset_converse(self, message):
        """Let skills know there was a problem with speech recognition"""
        lang = _get_message_lang(message)
        setup_locale(lang)  # restore default lang
        self.converse.converse_with_skills([], lang, message)

    def do_converse(self, utterances, skill_id, lang, message):
        """DEPRECATED: do not use, method only for api backwards compatibility

        Logs a warning and calls ConverseService.converse

        Args:
            utterances (list of tuples): utterances paired with normalized
                                         versions.
            skill_id: skill to query.
            lang (str): current language
            message (Message): message containing interaction info.
        """
        # NOTE: can not delete method for backwards compat with upstream
        LOG.warning("self.do_converse has been deprecated!\n"
                    "use self.converse.converse instead")
        return self.converse.converse(utterances, skill_id, lang, message)

    def handle_converse_error(self, message):
        """DEPRECATED: do not use, method only for api backwards compatibility
        Logs a warning
        """
        # NOTE: can not delete method for backwards compat with upstream
        LOG.warning("handle_converse_error has been deprecated!")

    def remove_active_skill(self, skill_id):
        """DEPRECATED: do not use, method only for api backwards compatibility

        Logs a warning and calls ConverseService.deactivate_skill

        Args:
            skill_id (str): skill to remove
        """
        # NOTE: can not delete method for backwards compat with upstream
        LOG.warning("self.remove_active_skill has been deprecated!\n"
                    "use self.converse.deactivate_skill instead")
        self.converse.deactivate_skill(skill_id)

    def add_active_skill(self, skill_id):
        """DEPRECATED: do not use, method only for api backwards compatibility

        Logs a warning and calls ConverseService.activate_skill

        Args:
            skill_id (str): identifier of skill to be added.
        """
        # NOTE: can not delete method for backwards compat with upstream
        LOG.warning("self.add_active_skill has been deprecated!\n"
                    "use self.converse.activate_skill instead")
        self.converse.activate_skill(skill_id)

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
            intent_type = f'{intent.skill_id}:converse'
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
        try:
            lang = _get_message_lang(message)
            setup_locale(lang)  # set default lang

            utterances = message.data.get('utterances', [])
            combined = _normalize_all_utterances(utterances)

            stopwatch = Stopwatch()

            # Create matchers
            padatious_matcher = PadatiousMatcher(self.padatious_service)

            # List of functions to use to match the utterance with intent.
            # These are listed in priority order.
            match_funcs = [
                self.converse.converse_with_skills, padatious_matcher.match_high,
                self.adapt_service.match_intent, self.fallback.high_prio,
                padatious_matcher.match_medium, self.fallback.medium_prio,
                padatious_matcher.match_low, self.fallback.low_prio
            ]

            match = None
            with stopwatch:
                # Loop through the matching functions until a match is found.
                for match_func in match_funcs:
                    match = match_func(combined, lang, message)
                    if match:
                        break
            if match:
                if match.skill_id:
                    self.converse.activate_skill(match.skill_id)
                    # If the service didn't report back the skill_id it
                    # takes on the responsibility of making the skill "active"

                # Launch skill if not handled by the match function
                if match.intent_type:
                    # keep all original message.data and update with intent
                    # match, mycroft-core only keeps "utterances"
                    data = dict(message.data)
                    data.update(match.intent_data)
                    reply = message.reply(match.intent_type, data)
                    self.bus.emit(reply)

            else:
                # Nothing was able to handle the intent
                # Ask politely for forgiveness for failing in this vital task
                self.send_complete_intent_failure(message)
            self.send_metrics(match, message.context, stopwatch)
        except Exception as err:
            LOG.exception(err)

    def send_complete_intent_failure(self, message):
        """Send a message that no skill could handle the utterance.

        Args:
            message (Message): original message to forward from
        """
        self.bus.emit(message.forward('complete_intent_failure'))

    def handle_register_vocab(self, message):
        """Register adapt vocabulary.

        Args:
            message (Message): message containing vocab info
        """
        # TODO: 22.02 Remove backwards compatibility
        if _is_old_style_keyword_message(message):
            LOG.warning('Deprecated: Registering keywords with old message. '
                        'This will be removed in v22.02.')
            _update_keyword_message(message)

        entity_value = message.data.get('entity_value')
        entity_type = message.data.get('entity_type')
        regex_str = message.data.get('regex')
        alias_of = message.data.get('alias_of')
        lang = _get_message_lang(message)
        self.adapt_service.register_vocabulary(entity_value, entity_type,
                                               alias_of, regex_str, lang)
        self.registered_vocab.append(message.data)

    def handle_register_intent(self, message):
        """Register adapt intent.

        Args:
            message (Message): message containing intent info
        """
        intent = open_intent_envelope(message)
        self.adapt_service.register_intent(intent)

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
        utterance = message.data["utterance"]
        lang = _get_message_lang(message)
        combined = _normalize_all_utterances([utterance])

        # Create matchers
        padatious_matcher = PadatiousMatcher(self.padatious_service)

        # List of functions to use to match the utterance with intent.
        # These are listed in priority order.
        # TODO once we have a mechanism for checking if a fallback will
        #  trigger without actually triggering it, those should be added here
        match_funcs = [
            padatious_matcher.match_high,
            self.adapt_service.match_intent,
            # self.fallback.high_prio,
            padatious_matcher.match_medium,
            # self.fallback.medium_prio,
            padatious_matcher.match_low,
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
                                    {"skills": self.converse.active_skills}))

    def handle_get_adapt(self, message):
        """handler getting the adapt response for an utterance.

        Args:
            message (Message): message containing utterance
        """
        utterance = message.data["utterance"]
        lang = _get_message_lang(message)
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


def _is_old_style_keyword_message(message):
    """Simple check that the message is not using the updated format.

    TODO: Remove in v22.02

    Args:
        message (Message): Message object to check

    Returns:
        (bool) True if this is an old messagem, else False
    """
    return ('entity_value' not in message.data and 'start' in message.data)


def _update_keyword_message(message):
    """Make old style keyword registration message compatible.

    Copies old keys in message data to new names.

    Args:
        message (Message): Message to update
    """
    message.data['entity_value'] = message.data['start']
    message.data['entity_type'] = message.data['end']
