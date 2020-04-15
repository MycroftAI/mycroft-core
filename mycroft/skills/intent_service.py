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
from copy import copy
import time
from adapt.context import ContextManagerFrame
from adapt.engine import IntentDeterminationEngine
from adapt.intent import IntentBuilder

from mycroft.configuration import Configuration
from mycroft.util.lang import set_active_lang
from mycroft.util.log import LOG
from mycroft.util.parse import normalize
from mycroft.metrics import report_timing, Stopwatch
from mycroft.skills.padatious_service import PadatiousService
from .intent_service_interface import open_intent_envelope


class AdaptIntent(IntentBuilder):
    def __init__(self, name=''):
        super().__init__(name)


def workaround_one_of_context(best_intent):
    """ Handle Adapt issue with context injection combined with one_of.

    For all entries in the intent result where the value is None try to
    populate using a value from the __tags__ structure.
    """
    for key in best_intent:
        if best_intent[key] is None:
            for t in best_intent['__tags__']:
                if key in t:
                    best_intent[key] = t[key][0]['entities'][0]['key']
    return best_intent


class ContextManager:
    """
    ContextManager
    Use to track context throughout the course of a conversational session.
    How to manage a session's lifecycle is not captured here.
    """

    def __init__(self, timeout):
        self.frame_stack = []
        self.timeout = timeout * 60  # minutes to seconds

    def clear_context(self):
        self.frame_stack = []

    def remove_context(self, context_id):
        self.frame_stack = [(f, t) for (f, t) in self.frame_stack
                            if context_id in f.entities[0].get('data', [])]

    def inject_context(self, entity, metadata=None):
        """
        Args:
            entity(object): Format example...
                               {'data': 'Entity tag as <str>',
                                'key': 'entity proper name as <str>',
                                'confidence': <float>'
                               }
            metadata(object): dict, arbitrary metadata about entity injected
        """
        metadata = metadata or {}
        try:
            if len(self.frame_stack) > 0:
                top_frame = self.frame_stack[0]
            else:
                top_frame = None
            if top_frame and top_frame[0].metadata_matches(metadata):
                top_frame[0].merge_context(entity, metadata)
            else:
                frame = ContextManagerFrame(entities=[entity],
                                            metadata=metadata.copy())
                self.frame_stack.insert(0, (frame, time.time()))
        except (IndexError, KeyError):
            pass

    def get_context(self, max_frames=None, missing_entities=None):
        """ Constructs a list of entities from the context.

        Args:
            max_frames(int): maximum number of frames to look back
            missing_entities(list of str): a list or set of tag names,
            as strings

        Returns:
            list: a list of entities
        """
        missing_entities = missing_entities or []

        relevant_frames = [frame[0] for frame in self.frame_stack if
                           time.time() - frame[1] < self.timeout]
        if not max_frames or max_frames > len(relevant_frames):
            max_frames = len(relevant_frames)

        missing_entities = list(missing_entities)
        context = []
        last = ''
        depth = 0
        for i in range(max_frames):
            frame_entities = [entity.copy() for entity in
                              relevant_frames[i].entities]
            for entity in frame_entities:
                entity['confidence'] = entity.get('confidence', 1.0) \
                                       / (2.0 + depth)
            context += frame_entities

            # Update depth
            if entity['origin'] != last or entity['origin'] == '':
                depth += 1
            last = entity['origin']

        result = []
        if len(missing_entities) > 0:
            for entity in context:
                if entity.get('data') in missing_entities:
                    result.append(entity)
                    # NOTE: this implies that we will only ever get one
                    # of an entity kind from context, unless specified
                    # multiple times in missing_entities. Cannot get
                    # an arbitrary number of an entity kind.
                    missing_entities.remove(entity.get('data'))
        else:
            result = context

        # Only use the latest instance of each keyword
        stripped = []
        processed = []
        for f in result:
            keyword = f['data'][0][1]
            if keyword not in processed:
                stripped.append(f)
                processed.append(keyword)
        result = stripped
        return result


class IntentService:
    def __init__(self, bus):
        self.config = Configuration.get().get('context', {})
        self.engine = IntentDeterminationEngine()

        # Dictionary for translating a skill id to a name
        self.skill_names = {}
        # Context related intializations
        self.context_keywords = self.config.get('keywords', [])
        self.context_max_frames = self.config.get('max_frames', 3)
        self.context_timeout = self.config.get('timeout', 2)
        self.context_greedy = self.config.get('greedy', False)
        self.context_manager = ContextManager(self.context_timeout)
        self.bus = bus
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

        def add_active_skill_handler(message):
            self.add_active_skill(message.data['skill_id'])

        self.bus.on('active_skill_request', add_active_skill_handler)
        self.active_skills = []  # [skill_id , timestamp]
        self.converse_timeout = 5  # minutes to prune active_skills

        # Intents API
        self.registered_intents = []
        self.registered_vocab = []
        self.bus.on('intent.service.adapt.get', self.handle_get_adapt)
        self.bus.on('intent.service.intent.get', self.handle_get_intent)
        self.bus.on('intent.service.skills.get', self.handle_get_skills)
        self.bus.on('intent.service.active_skills.get',
                    self.handle_get_active_skills)
        self.bus.on('intent.service.adapt.manifest.get', self.handle_manifest)
        self.bus.on('intent.service.adapt.vocab.manifest.get',
                    self.handle_vocab_manifest)

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
        lang = message.data.get('lang', "en-us")
        set_active_lang(lang)
        for skill in copy(self.active_skills):
            self.do_converse(None, skill[0], lang, message)

    def do_converse(self, utterances, skill_id, lang, message):
        converse_msg = (message.reply("skill.converse.request", {
            "skill_id": skill_id, "utterances": utterances, "lang": lang}))
        result = self.bus.wait_for_response(converse_msg,
                                            'skill.converse.response')
        if result and 'error' in result.data:
            self.handle_converse_error(result)
            return False
        elif result is not None:
            return result.data.get('result', False)
        else:
            return False

    def handle_converse_error(self, message):
        LOG.error(message.data['error'])
        skill_id = message.data["skill_id"]
        if message.data["error"] == "skill id does not exist":
            self.remove_active_skill(skill_id)

    def remove_active_skill(self, skill_id):
        for skill in self.active_skills:
            if skill[0] == skill_id:
                self.active_skills.remove(skill)

    def add_active_skill(self, skill_id):
        """Add a skill or update the position of an active skill.

        The skill is added to the front of the list, if it's already in the
        list it's removed so there is only a single entry of it.

        Arguments:
            skill_id (str): identifier of skill to be added.
        """
        # search the list for an existing entry that already contains it
        # and remove that reference
        if skill_id != '':
            self.remove_active_skill(skill_id)
            # add skill with timestamp to start of skill_list
            self.active_skills.insert(0, [skill_id, time.time()])
        else:
            LOG.warning('Skill ID was empty, won\'t add to list of '
                        'active skills.')

    def update_context(self, intent):
        """Updates context with keyword from the intent.

        NOTE: This method currently won't handle one_of intent keywords
              since it's not using quite the same format as other intent
              keywords. This is under investigation in adapt, PR pending.

        Args:
            intent: Intent to scan for keywords
        """
        for tag in intent['__tags__']:
            if 'entities' not in tag:
                continue
            context_entity = tag['entities'][0]
            if self.context_greedy:
                self.context_manager.inject_context(context_entity)
            elif context_entity['data'][0][1] in self.context_keywords:
                self.context_manager.inject_context(context_entity)

    def send_metrics(self, intent, context, stopwatch):
        """Send timing metrics to the backend.

        NOTE: This only applies to those with Opt In.
        """
        ident = context['ident'] if 'ident' in context else None
        if intent:
            # Recreate skill name from skill id
            parts = intent.get('intent_type', '').split(':')
            intent_type = self.get_skill_name(parts[0])
            if len(parts) > 1:
                intent_type = ':'.join([intent_type] + parts[1:])
            report_timing(ident, 'intent_service', stopwatch,
                          {'intent_type': intent_type})
        else:
            report_timing(ident, 'intent_service', stopwatch,
                          {'intent_type': 'intent_failure'})

    def handle_utterance(self, message):
        """Main entrypoint for handling user utterances with Mycroft skills

        Monitor the messagebus for 'recognizer_loop:utterance', typically
        generated by a spoken interaction but potentially also from a CLI
        or other method of injecting a 'user utterance' into the system.

        Utterances then work through this sequence to be handled:
        1) Active skills attempt to handle using converse()
        2) Padatious high match intents (conf > 0.95)
        3) Adapt intent handlers
        5) Fallbacks:
           - Padatious near match intents (conf > 0.8)
           - General fallbacks
           - Padatious loose match intents (conf > 0.5)
           - Unknown intent handler

        Args:
            message (Message): The messagebus data
        """
        try:
            # Get language of the utterance
            lang = message.data.get('lang', "en-us")
            set_active_lang(lang)

            utterances = message.data.get('utterances', [])
            # normalize() changes "it's a boy" to "it is a boy", etc.
            norm_utterances = [normalize(u.lower(), remove_articles=False)
                               for u in utterances]

            # Build list with raw utterance(s) first, then optionally a
            # normalized version following.
            combined = utterances + list(set(norm_utterances) -
                                         set(utterances))
            LOG.debug("Utterances: {}".format(combined))

            stopwatch = Stopwatch()
            intent = None
            padatious_intent = None
            with stopwatch:
                # Give active skills an opportunity to handle the utterance
                converse = self._converse(combined, lang, message)

                if not converse:
                    # No conversation, use intent system to handle utterance
                    intent = self._adapt_intent_match(utterances,
                                                      norm_utterances, lang)
                    for utt in combined:
                        _intent = PadatiousService.instance.calc_intent(utt)
                        if _intent:
                            best = padatious_intent.conf if padatious_intent \
                                else 0.0
                            if best < _intent.conf:
                                padatious_intent = _intent
                    LOG.debug("Padatious intent: {}".format(padatious_intent))
                    LOG.debug("    Adapt intent: {}".format(intent))

            if converse:
                # Report that converse handled the intent and return
                LOG.debug("Handled in converse()")
                ident = None
                if message.context and 'ident' in message.context:
                    ident = message.context['ident']
                report_timing(ident, 'intent_service', stopwatch,
                              {'intent_type': 'converse'})
                return
            elif (intent and intent.get('confidence', 0.0) > 0.0 and
                  not (padatious_intent and padatious_intent.conf >= 0.95)):
                # Send the message to the Adapt intent's handler unless
                # Padatious is REALLY sure it was directed at it instead.
                self.update_context(intent)
                # update active skills
                skill_id = intent['intent_type'].split(":")[0]
                self.add_active_skill(skill_id)
                # Adapt doesn't handle context injection for one_of keywords
                # correctly. Workaround this issue if possible.
                try:
                    intent = workaround_one_of_context(intent)
                except LookupError:
                    LOG.error('Error during workaround_one_of_context')
                reply = message.reply(intent.get('intent_type'), intent)
            else:
                # Allow fallback system to handle utterance
                # NOTE: A matched padatious_intent is handled this way, too
                # TODO: Need to redefine intent_failure when STT can return
                #       multiple hypothesis -- i.e. len(utterances) > 1
                reply = message.reply('intent_failure',
                                      {'utterance': utterances[0],
                                       'norm_utt': norm_utterances[0],
                                       'lang': lang})
            self.bus.emit(reply)
            self.send_metrics(intent, message.context, stopwatch)
        except Exception as e:
            LOG.exception(e)

    def _converse(self, utterances, lang, message):
        """Give active skills a chance at the utterance

        Args:
            utterances (list):  list of utterances
            lang (string):      4 letter ISO language code
            message (Message):  message to use to generate reply

        Returns:
            bool: True if converse handled it, False if  no skill processes it
        """

        # check for conversation time-out
        self.active_skills = [skill for skill in self.active_skills
                              if time.time() - skill[
                                  1] <= self.converse_timeout * 60]

        # check if any skill wants to handle utterance
        for skill in copy(self.active_skills):
            if self.do_converse(utterances, skill[0], lang, message):
                # update timestamp, or there will be a timeout where
                # intent stops conversing whether its being used or not
                self.add_active_skill(skill[0])
                return True
        return False

    def _adapt_intent_match(self, raw_utt, norm_utt, lang):
        """Run the Adapt engine to search for an matching intent

        Args:
            raw_utt (list):  list of utterances
            norm_utt (list): same list of utterances, normalized
            lang (string):   language code, e.g "en-us"

        Returns:
            Intent structure, or None if no match was found.
        """
        best_intent = None

        def take_best(intent, utt):
            nonlocal best_intent
            best = best_intent.get('confidence', 0.0) if best_intent else 0.0
            conf = intent.get('confidence', 0.0)
            if conf > best:
                best_intent = intent
                # TODO - Shouldn't Adapt do this?
                best_intent['utterance'] = utt

        for idx, utt in enumerate(raw_utt):
            try:
                intents = [i for i in self.engine.determine_intent(
                    utt, 100,
                    include_tags=True,
                    context_manager=self.context_manager)]
                if intents:
                    take_best(intents[0], utt)

                # Also test the normalized version, but set the utterance to
                # the raw version so skill has access to original STT
                norm_intents = [i for i in self.engine.determine_intent(
                    norm_utt[idx], 100,
                    include_tags=True,
                    context_manager=self.context_manager)]
                if norm_intents:
                    take_best(norm_intents[0], utt)
            except Exception as e:
                LOG.exception(e)
        return best_intent

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
        self.registered_vocab.append(message.data)

    def handle_register_intent(self, message):
        intent = open_intent_envelope(message)
        self.engine.register_intent_parser(intent)

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
        self.context_manager.inject_context(entity)

    def handle_remove_context(self, message):
        """Remove specific context

        Args:
            message: data contains the 'context' item to remove
        """
        context = message.data.get('context')
        if context:
            self.context_manager.remove_context(context)

    def handle_clear_context(self, message):
        """Clears all keywords from context """
        self.context_manager.clear_context()

    def handle_get_adapt(self, message):
        utterance = message.data["utterance"]
        lang = message.data.get("lang", "en-us")
        norm = normalize(utterance, lang, remove_articles=False)
        intent = self._adapt_intent_match([utterance], [norm], lang)
        self.bus.emit(message.reply("intent.service.adapt.reply",
                                    {"intent": intent}))

    def handle_get_intent(self, message):
        utterance = message.data["utterance"]
        lang = message.data.get("lang", "en-us")
        norm = normalize(utterance, lang, remove_articles=False)
        intent = self._adapt_intent_match([utterance], [norm], lang)
        # Adapt intent's handler is used unless
        # Padatious is REALLY sure it was directed at it instead.
        padatious_intent = PadatiousService.instance.calc_intent(utterance)
        if not padatious_intent and norm != utterance:
            padatious_intent = PadatiousService.instance.calc_intent(norm)
        if intent is None or (
                padatious_intent and padatious_intent.conf >= 0.95):
            intent = padatious_intent.__dict__
        self.bus.emit(message.reply("intent.service.intent.reply",
                                    {"intent": intent}))

    def handle_get_skills(self, message):
        self.bus.emit(message.reply("intent.service.skills.reply",
                                    {"skills": self.skill_names}))

    def handle_get_active_skills(self, message):
        self.bus.emit(message.reply("intent.service.active_skills.reply",
                                    {"skills": [s[0] for s in
                                                self.active_skills]}))

    def handle_manifest(self, message):
        self.bus.emit(message.reply("intent.service.adapt.manifest",
                                    {"intents": self.registered_intents}))

    def handle_vocab_manifest(self, message):
        self.bus.emit(message.reply("intent.service.adapt.vocab.manifest",
                                    {"vocab": self.registered_vocab}))
