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
from mycroft.skills.core import open_intent_envelope
from mycroft.util.log import getLogger
from mycroft.util.parse import normalize
from adapt.context import ContextManagerFrame
import time
__author__ = 'seanfitz'

logger = getLogger(__name__)


class ContextManager(object):
    """
    ContextManager
    Use to track context throughout the course of a conversational session.
    How to manage a session's lifecycle is not captured here.
    """
    def __init__(self):
        self.frame_stack = []

    def clear_context(self):
        self.frame_stack = []

    def remove_context(self, context_id):
        self.frame_stack = [f for f in self.frame_stack
                            if context_id in f.get('data', [])]

    def inject_context(self, entity, metadata={}):
        """
        Args:
            entity(object):
                format {'data': 'Entity tag as <str>',
                        'key': 'entity proper name as <str>',
                         'confidence': <float>'
                         }
            metadata(object): dict, arbitrary metadata about the entity being
            added
        """
        top_frame = self.frame_stack[0] if len(self.frame_stack) > 0 else None
        if top_frame and top_frame[0].metadata_matches(metadata):
            top_frame[0].merge_context(entity, metadata)
        else:
            frame = ContextManagerFrame(entities=[entity],
                                        metadata=metadata.copy())
            self.frame_stack.insert(0, (frame, time.time()))

    def get_context(self, max_frames=None, missing_entities=[]):
        """
        Constructs a list of entities from the context.

        Args:
            max_frames(int): maximum number of frames to look back
            missing_entities(list of str): a list or set of tag names,
            as strings

        Returns:
            list: a list of entities
        """
        relevant_frames = [frame[0] for frame in self.frame_stack if
                           time.time() - frame[1] < 120]
        if not max_frames or max_frames > len(relevant_frames):
            max_frames = len(relevant_frames)

        missing_entities = list(missing_entities)
        context = []
        for i in xrange(max_frames):
            frame_entities = [entity.copy() for entity in
                              relevant_frames[i].entities]
            for entity in frame_entities:
                entity['confidence'] = entity.get('confidence', 1.0) \
                    / (2.0 + i)
            context += frame_entities

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
        print result
        print "RETURNING!"
        return result


class IntentService(object):
    def __init__(self, emitter):
        self.engine = IntentDeterminationEngine()
        self.context_manager = ContextManager()
        self.emitter = emitter
        self.emitter.on('register_vocab', self.handle_register_vocab)
        self.emitter.on('register_intent', self.handle_register_intent)
        self.emitter.on('recognizer_loop:utterance', self.handle_utterance)
        self.emitter.on('detach_intent', self.handle_detach_intent)
        self.emitter.on('detach_skill', self.handle_detach_skill)
        # Context related handlers
        self.emitter.on('add_context', self.handle_add_context)
        self.emitter.on('remove_context', self.handle_remove_context)
        self.emitter.on('clear_context', self.handle_clear_context)

    def handle_utterance(self, message):
        # Get language of the utterance
        lang = message.data.get('lang', None)
        if not lang:
            lang = "en-us"

        utterances = message.data.get('utterances', '')

        best_intent = None
        for utterance in utterances:
            try:
                print "HANDLING INTENT"
                # normalize() changes "it's a boy" to "it is boy", etc.
                best_intent = next(self.engine.determine_intent(
                                   normalize(utterance, lang), 100,
                                   include_tags=True,
                                   context_manager=self.context_manager))
                print "DONE"
                # TODO - Should Adapt handle this?
                best_intent['utterance'] = utterance
            except StopIteration, e:
                logger.exception(e)
                continue

        if best_intent and best_intent.get('confidence', 0.0) > 0.0:
            for tag in best_intent['__tags__']:
                context_entity = tag.get('entities')[0]
                self.context_manager.inject_context(context_entity)
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

    def handle_add_context(self, message):
        entity = {'confidence': 1.0}
        context = message.data.get('context')
        word = message.data.get('word')
        print "Adding " + context
        entity['data'] = [(word, context)]
        entity['match'] = word
        entity['key'] = word
        self.context_manager.inject_context(entity)

    def handle_remove_context(self, message):
        context = message.data.get('context')
        self.context_manager.remove_context(context)

    def handle_clear_context(self, message):
        self.context_manager.clear_context()
