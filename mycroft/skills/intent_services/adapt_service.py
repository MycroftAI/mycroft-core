# Copyright 2020 Mycroft AI Inc.
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
"""An intent parsing service using the Adapt parser."""
from threading import Lock
import time

from adapt.context import ContextManagerFrame
from adapt.engine import IntentDeterminationEngine
from adapt.intent import IntentBuilder

from mycroft.configuration import Configuration
from mycroft.util.log import LOG
from mycroft.skills.intent_services.base import IntentMatch


def _entity_skill_id(skill_id):
    """Helper converting a skill id to the format used in entities.

    Arguments:
        skill_id (str): skill identifier

    Returns:
        (str) skill id on the format used by skill entities
    """
    skill_id = skill_id[:-1]
    skill_id = skill_id.replace('.', '_')
    skill_id = skill_id.replace('-', '_')
    return skill_id


class AdaptIntent(IntentBuilder):
    """Wrapper for IntentBuilder setting a blank name.

    Args:
        name (str): Optional name of intent
    """

    def __init__(self, name=''):
        super().__init__(name)


def _strip_result(context_features):
    """Keep only the latest instance of each keyword.

    Arguments
        context_features (iterable): context features to check.
    """
    stripped = []
    processed = []
    for feature in context_features:
        keyword = feature['data'][0][1]
        if keyword not in processed:
            stripped.append(feature)
            processed.append(keyword)
    return stripped


class ContextManager:
    """Adapt Context Manager

    Use to track context throughout the course of a conversational session.
    How to manage a session's lifecycle is not captured here.
    """

    def __init__(self, timeout):
        self.frame_stack = []
        self.timeout = timeout * 60  # minutes to seconds

    def clear_context(self):
        """Remove all contexts."""
        self.frame_stack = []

    def remove_context(self, context_id):
        """Remove a specific context entry.

        Args:
            context_id (str): context entry to remove
        """
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
            if self.frame_stack:
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
        entity = {}
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
        if missing_entities:
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

        # Only use the latest  keyword
        return _strip_result(result)


class AdaptService:
    """Intent service wrapping the Apdapt intent Parser."""

    def __init__(self, config):
        self.config = config

        self.lang = Configuration.get().get("lang", "en-us")
        langs = Configuration.get().get('secondary_langs') or []
        if self.lang not in langs:
            langs.append(self.lang)

        self.engines = {lang: IntentDeterminationEngine()
                        for lang in langs}
        # Context related intializations
        self.context_keywords = self.config.get('keywords', [])
        self.context_max_frames = self.config.get('max_frames', 3)
        self.context_timeout = self.config.get('timeout', 2)
        self.context_greedy = self.config.get('greedy', False)
        self.context_manager = ContextManager(self.context_timeout)
        self.lock = Lock()

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

    def match_intent(self, utterances, lang=None, __=None):
        """Run the Adapt engine to search for an matching intent.

        Args:
            utterances (iterable): utterances for consideration in intent
            matching. As a practical matter, a single utterance will be
            passed in most cases.  But there are instances, such as
            streaming STT that could pass multiple.  Each utterance
            is represented as a tuple containing the raw, normalized, and
            possibly other variations of the utterance.

        Returns:
            Intent structure, or None if no match was found.
        """
        lang = lang or self.lang
        if lang not in self.engines:
            return None

        best_intent = {}

        def take_best(intent, utt):
            nonlocal best_intent
            best = best_intent.get('confidence', 0.0) if best_intent else 0.0
            conf = intent.get('confidence', 0.0)
            if conf > best:
                best_intent = intent
                # TODO - Shouldn't Adapt do this?
                best_intent['utterance'] = utt

        for utt_tup in utterances:
            for utt in utt_tup:
                try:
                    intents = [i for i in self.engines[lang].determine_intent(
                        utt, 100,
                        include_tags=True,
                        context_manager=self.context_manager)]
                    if intents:
                        utt_best = max(
                            intents, key=lambda x: x.get('confidence', 0.0)
                        )
                        take_best(utt_best, utt_tup[0])

                except Exception as err:
                    LOG.exception(err)

        if best_intent:
            self.update_context(best_intent)
            skill_id = best_intent['intent_type'].split(":")[0]
            ret = IntentMatch(
                'Adapt', best_intent['intent_type'], best_intent, skill_id
            )
        else:
            ret = None
        return ret

    def register_vocab(self, start_concept, end_concept,
                       alias_of, regex_str, lang):
        """Register Vocabulary. DEPRECATED

        This method should not be used, it has been replaced by
        register_vocabulary().
        """
        self.register_vocabulary(start_concept, end_concept, alias_of,
                                 regex_str, lang)

    def register_vocabulary(self, entity_value, entity_type,
                            alias_of, regex_str, lang):
        """Register skill vocabulary as adapt entity.

        This will handle both regex registration and registration of normal
        keywords. if the "regex_str" argument is set all other arguments will
        be ignored.

        Argument:
            entity_value: the natural langauge word
            entity_type: the type/tag of an entity instance
            alias_of: entity this is an alternative for
        """
        if lang in self.engines:
            with self.lock:
                if regex_str:
                    self.engines[lang].register_regex_entity(regex_str)
                else:
                    self.engines[lang].register_entity(
                        entity_value, entity_type, alias_of=alias_of)

    def register_intent(self, intent):
        """Register new intent with adapt engine.

        Args:
            intent (IntentParser): IntentParser to register
        """
        for lang in self.engines:
            with self.lock:
                self.engines[lang].register_intent_parser(intent)

    def detach_skill(self, skill_id):
        """Remove all intents for skill.

        Args:
            skill_id (str): skill to process
        """
        with self.lock:
            for lang in self.engines:
                skill_parsers = [
                    p.name for p in self.engines[lang].intent_parsers if
                    p.name.startswith(skill_id)
                ]
                self.engines[lang].drop_intent_parser(skill_parsers)
            self._detach_skill_keywords(skill_id)
            self._detach_skill_regexes(skill_id)

    def _detach_skill_keywords(self, skill_id):
        """Detach all keywords registered with a particular skill.

        Arguments:
            skill_id (str): skill identifier
        """
        skill_id = _entity_skill_id(skill_id)

        def match_skill_entities(data):
            return data and data[1].startswith(skill_id)

        for lang in self.engines:
            self.engines[lang].drop_entity(match_func=match_skill_entities)

    def _detach_skill_regexes(self, skill_id):
        """Detach all regexes registered with a particular skill.

        Arguments:
            skill_id (str): skill identifier
        """
        skill_id = _entity_skill_id(skill_id)

        def match_skill_regexes(regexp):
            return any([r.startswith(skill_id)
                        for r in regexp.groupindex.keys()])

        for lang in self.engines:
            self.engines[lang].drop_regex_entity(match_func=match_skill_regexes)

    def detach_intent(self, intent_name):
        """Detatch a single intent

        Args:
            intent_name (str): Identifier for intent to remove.
        """
        for lang in self.engines:
            new_parsers = [
                p for p in self.engines[lang].intent_parsers if p.name != intent_name
            ]
            self.engines[lang].intent_parsers = new_parsers
