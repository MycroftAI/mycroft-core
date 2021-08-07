# Copyright 2018 Mycroft AI Inc.
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

import pyee
import time
from adapt.expander import BronKerboschExpander
from adapt.tools.text.trie import Trie

__author__ = 'seanfitz'


class Parser(pyee.EventEmitter):
    """
    Coordinate a tagger and expander to yield valid parse results.
    """
    def __init__(self, tokenizer, tagger):
        pyee.EventEmitter.__init__(self)
        self._tokenizer = tokenizer
        self._tagger = tagger

    def parse(self, utterance, context=None, N=1):
        """Used to find tags within utterance with a given confidence

        Args:
            utterance(str): conversational piece given by the user
            context(list): a list of entities
            N(int): number of results
        Returns: yield an object with the following fields
            utterance(str): the value passed in
            tags(list) : a list of tags found in utterance
            time(time) : duration since call of function
            confidence(float) : float indicating how confident of a match to the
                utterance. This might be used to determan the most likely intent.

        """
        start = time.time()
        context_trie = None
        if context and isinstance(context, list):
            # sort by confidence in ascending order, so
            # highest confidence for an entity is last.
            # see comment on TrieNode ctor
            context.sort(key=lambda x: x.get('confidence'))

            context_trie = Trie()
            for entity in context:
                entity_value, entity_type = entity.get('data')[0]
                context_trie.insert(entity_value.lower(),
                                    data=(entity_value, entity_type),
                                    weight=entity.get('confidence'))

        tagged = self._tagger.tag(utterance.lower(), context_trie=context_trie)
        self.emit("tagged_entities",
                  {
                      'utterance': utterance,
                      'tags': list(tagged),
                      'time': time.time() - start
                  })
        start = time.time()
        bke = BronKerboschExpander(self._tokenizer)

        def score_clique(clique):
            score = 0.0
            for tagged_entity in clique:
                ec = tagged_entity.get('entities', [{'confidence': 0.0}])[0].get('confidence')
                score += ec * len(tagged_entity.get('entities', [{'match': ''}])[0].get('match')) / (
                    len(utterance) + 1)
            return score

        parse_results = bke.expand(tagged, clique_scoring_func=score_clique)
        count = 0
        for result in parse_results:
            count += 1
            parse_confidence = 0.0
            for tag in result:
                sample_entity = tag['entities'][0]
                entity_confidence = sample_entity.get('confidence', 0.0) * float(
                    len(sample_entity.get('match'))) / len(utterance)
                parse_confidence += entity_confidence
            yield {
                'utterance': utterance,
                'tags': result,
                'time': time.time() - start,
                'confidence': parse_confidence
            }

            if count >= N:
                break
