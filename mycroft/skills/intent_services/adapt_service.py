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

from adapt.context import ContextManager as AdaptContextManager
from adapt.engine import IntentDeterminationEngine
from adapt.intent import IntentBuilder

from mycroft.util.log import LOG
from .base import IntentMatch


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


def _frame_timedout(frame, timeout):
    """Check if a frame has timed out using it's metadata.

    frame (ContextManagerFrame):
    """
    current_time = time.monotonic()
    return current_time > frame.metadata['timestamp'] + timeout


class ContextManager(AdaptContextManager):
    """Adapt Context Manager

    This class extends the default ContextManager in adapt to "timeout"
    context frames after a set time. it also limits the context returned
    to a single entry.
    """
    def __init__(self, timeout):
        super().__init__()
        self.timeout = timeout * 60  # minutes to seconds

    def clear_context(self):
        """Remove all contexts."""
        self.frame_stack = []

    def remove_context(self, context_id):
        """Remove a specific context entry.

        Args:
            context_id (str): context entry to remove
        """
        self.frame_stack = [frame for frame in self.frame_stack
                            if context_id in frame.entities[0].get('data', [])]

    def get_context(self, max_frames=None, missing_entities=[]):
        """Extends the get_context from Adapt's ContextManager.

        Extensions on top of parent class:
        - Timeout Context frames after a set time
        - Only return the most recent matching entity

        Arguments:
            max_frames(int): maximum number of frames to look back
            missing_entities(list of str): a list or set of tag names,
            as strings

        Returns:
            list: a list of entities
        """
        self.frame_stack = [frame for frame in self.frame_stack
                            if not _frame_timedout(frame, self.timeout)]
        result = super().get_context(max_frames, missing_entities)
        # Only use the latest keyword
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
        self.lock = Lock()

    def add_context(self, entity):
        """Add entity to context."""
        self.context_manager.inject_context(
            entity,
            metadata={'timestamp': time.monotonic()}
        )

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
                self.add_context(context_entity)
            elif context_entity['data'][0][1] in self.context_keywords:
                self.add_context(context_entity)

    def match_intent(self, utterances, _=None, __=None):
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

    # TODO 22.02: Remove this deprecated method
    def register_vocab(self, start_concept, end_concept, alias_of, regex_str):
        """Register Vocabulary. DEPRECATED

        This method should not be used, it has been replaced by
        register_vocabulary().
        """
        self.register_vocabulary(start_concept, end_concept,
                                 alias_of, regex_str)

    def register_vocabulary(self, entity_value, entity_type,
                            alias_of, regex_str):
        """Register skill vocabulary as adapt entity.

        This will handle both regex registration and registration of normal
        keywords. if the "regex_str" argument is set all other arguments will
        be ignored.

        Argument:
            entity_value: the natural langauge word
            entity_type: the type/tag of an entity instance
            alias_of: entity this is an alternative for
        """
        with self.lock:
            if regex_str:
                self.engine.register_regex_entity(regex_str)
            else:
                self.engine.register_entity(
                    entity_value, entity_type, alias_of=alias_of)

    def register_intent(self, intent):
        """Register new intent with adapt engine.

        Args:
            intent (IntentParser): IntentParser to register
        """
        with self.lock:
            self.engine.register_intent_parser(intent)

    def detach_skill(self, skill_id):
        """Remove all intents for skill.

        Args:
            skill_id (str): skill to process
        """
        with self.lock:
            skill_parsers = [
                p.name for p in self.engine.intent_parsers if
                p.name.startswith(skill_id)
            ]
            self.engine.drop_intent_parser(skill_parsers)
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

        self.engine.drop_entity(match_func=match_skill_entities)

    def _detach_skill_regexes(self, skill_id):
        """Detach all regexes registered with a particular skill.

        Arguments:
            skill_id (str): skill identifier
        """
        skill_id = _entity_skill_id(skill_id)

        def match_skill_regexes(regexp):
            return any([r.startswith(skill_id)
                        for r in regexp.groupindex.keys()])

        self.engine.drop_regex_entity(match_func=match_skill_regexes)

    def detach_intent(self, intent_name):
        """Detatch a single intent

        Args:
            intent_name (str): Identifier for intent to remove.
        """
        new_parsers = [
            p for p in self.engine.intent_parsers if p.name != intent_name
        ]
        self.engine.intent_parsers = new_parsers
