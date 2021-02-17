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
import time

from adapt.context import ContextManagerFrame
from adapt.engine import IntentDeterminationEngine
from adapt.intent import IntentBuilder

from mycroft.util.log import LOG
from .base import IntentMatch


class AdaptIntent(IntentBuilder):
    """Wrapper for IntentBuilder setting a blank name.

    Arguments:
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

        Arguments:
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
        self.engine = IntentDeterminationEngine()
        # Context related intializations
        self.context_keywords = self.config.get('keywords', [])
        self.context_max_frames = self.config.get('max_frames', 3)
        self.context_timeout = self.config.get('timeout', 2)
        self.context_greedy = self.config.get('greedy', False)
        self.context_manager = ContextManager(self.context_timeout)

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

    def match_intent(self, utterances, _=None, __=None):
        """Run the Adapt engine to search for an matching intent.

        Arguments:
            utterances (iterable): iterable of utterances, expected order
                                   [raw, normalized, other]

        Returns:
            Intent structure, or None if no match was found.
        """
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
                    intents = [i for i in self.engine.determine_intent(
                        utt, 100,
                        include_tags=True,
                        context_manager=self.context_manager)]
                    if intents:
                        take_best(intents[0], utt_tup[0])

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

    def register_vocab(self, start_concept, end_concept, alias_of, regex_str):
        """Register vocabulary."""
        if regex_str:
            self.engine.register_regex_entity(regex_str)
        else:
            self.engine.register_entity(
                start_concept, end_concept, alias_of=alias_of)

    def register_intent(self, intent):
        """Register new intent with adapt engine.

        Arguments:
            intent (IntentParser): IntentParser to register
        """
        self.engine.register_intent_parser(intent)

    def detach_skill(self, skill_id):
        """Remove all intents for skill.

        Arguments:
            skill_id (str): skill to process
        """
        new_parsers = [
            p for p in self.engine.intent_parsers if
            not p.name.startswith(skill_id)
        ]
        self.engine.intent_parsers = new_parsers

    def detach_intent(self, intent_name):
        """Detatch a single intent

        Arguments:
            intent_name (str): Identifier for intent to remove.
        """
        new_parsers = [
            p for p in self.engine.intent_parsers if p.name != intent_name
        ]
        self.engine.intent_parsers = new_parsers
