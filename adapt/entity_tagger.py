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

from adapt.tools.text.trie import Trie
from six.moves import xrange

__author__ = 'seanfitz'


class EntityTagger(object):
    """
    Known Entity Tagger
    Given an index of known entities, can efficiently search for those entities within a provided utterance.
    """
    def __init__(self, trie, tokenizer, regex_entities=[], max_tokens=20):
        self.trie = trie
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.regex_entities = regex_entities

    def _iterate_subsequences(self, tokens):
        """
        Using regex invokes this function, which significantly impacts performance of adapt. it is an N! operation.

        Args:
            tokens(list): list of tokens for Yield results.

        Yields:
            str: ?
        """
        for start_idx in xrange(len(tokens)):
            for end_idx in xrange(start_idx + 1, len(tokens) + 1):
                yield ' '.join(tokens[start_idx:end_idx]), start_idx

    def _sort_and_merge_tags(self, tags):
        decorated = [(tag['start_token'], tag['end_token'], tag) for tag in tags]
        decorated.sort(key=lambda x: (x[0], x[1]))
        return [tag for start_token, end_token, tag in decorated]

    def tag(self, utterance, context_trie=None):
        """
        Tag known entities within the utterance.
        Args:
            utterance(str): a string of natural language text
            context_trie(trie): optional, a trie containing only entities from context
                for this request

        Returns: dictionary, with the following keys
            match(str): the proper entity matched
            key(str): the string that was matched to the entity
            start_token(int): 0-based index of the first token matched
            end_token(int): 0-based index of the last token matched
            entities(list): a list of entity kinds as strings (Ex: Artist, Location)
        """
        tokens = self.tokenizer.tokenize(utterance)
        entities = []
        if len(self.regex_entities) > 0:
            for part, idx in self._iterate_subsequences(tokens):
                local_trie = Trie()
                for regex_entity in self.regex_entities:
                    match = regex_entity.match(part)
                    groups = match.groupdict() if match else {}
                    for key in list(groups):
                        match_str = groups.get(key)
                        local_trie.insert(match_str, (match_str, key))
                sub_tagger = EntityTagger(local_trie, self.tokenizer, max_tokens=self.max_tokens)
                for sub_entity in sub_tagger.tag(part):
                    sub_entity['start_token'] += idx
                    sub_entity['end_token'] += idx
                    for e in sub_entity['entities']:
                        e['confidence'] = 0.5
                    entities.append(sub_entity)
        additional_sort = len(entities) > 0

        context_entities = []
        for i in xrange(len(tokens)):
            part = ' '.join(tokens[i:])

            for new_entity in self.trie.gather(part):
                new_entity['data'] = list(new_entity['data'])
                entities.append({
                    'match': new_entity.get('match'),
                    'key': new_entity.get('key'),
                    'start_token': i,
                    'entities': [new_entity],
                    'end_token': i + len(self.tokenizer.tokenize(new_entity.get('match'))) - 1,
                    'from_context': False
                })

            if context_trie:
                for new_entity in context_trie.gather(part):
                    new_entity['data'] = list(new_entity['data'])
                    new_entity['confidence'] *= 2.0  # context entities get double the weight!
                    context_entities.append({
                        'match': new_entity.get('match'),
                        'key': new_entity.get('key'),
                        'start_token': i,
                        'entities': [new_entity],
                        'end_token': i + len(self.tokenizer.tokenize(new_entity.get('match'))) - 1,
                        'from_context': True
                    })

        additional_sort = additional_sort or len(entities) > 0

        if additional_sort:
            entities = self._sort_and_merge_tags(entities + context_entities)

        return entities
