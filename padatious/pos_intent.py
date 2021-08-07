# Copyright 2017 Mycroft AI, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math

from padatious.entity_edge import EntityEdge
from padatious.match_data import MatchData


class PosIntent(object):
    """
    Positional intent
    Used to extract entities

    Args:
        token (str): token to attach to (something like {word})
    """

    def __init__(self, token, intent_name=''):
        self.token = token
        self.edges = [EntityEdge(-1, token, intent_name), EntityEdge(+1, token, intent_name)]

    def match(self, orig_data, entity=None):
        l_matches = [(self.edges[0].match(orig_data.sent, pos), pos)
                     for pos in range(len(orig_data.sent))]
        r_matches = [(self.edges[1].match(orig_data.sent, pos), pos)
                     for pos in range(len(orig_data.sent))]

        def is_valid(l_pos, r_pos):
            if r_pos < l_pos:
                return False
            for p in range(l_pos, r_pos + 1):
                if orig_data.sent[p].startswith('{'):
                    return False
            return True

        possible_matches = []
        for l_conf, l_pos in l_matches:
            if l_conf < 0.2:
                continue
            for r_conf, r_pos in r_matches:
                if r_conf < 0.2:
                    continue
                if not is_valid(l_pos, r_pos):
                    continue

                extracted = orig_data.sent[l_pos:r_pos + 1]

                pos_conf = (l_conf - 0.5 + r_conf - 0.5) / 2 + 0.5
                ent_conf = (entity.match(extracted) if entity else 1)

                new_sent = orig_data.sent[:l_pos] + [self.token] + orig_data.sent[r_pos + 1:]
                new_matches = orig_data.matches.copy()
                new_matches[self.token] = extracted

                extra_conf = math.sqrt(pos_conf * ent_conf) - 0.5
                data = MatchData(orig_data.name, new_sent, new_matches,
                                 orig_data.conf + extra_conf)
                possible_matches.append(data)
        return possible_matches

    def save(self, prefix):
        prefix += '.' + self.token
        for i in self.edges:
            i.save(prefix)

    @classmethod
    def from_file(cls, prefix, token):
        prefix += '.' + token
        self = cls(token)
        for i in self.edges:
            i.load(prefix)
        return self

    def train(self, train_data):
        for i in self.edges:
            i.train(train_data)
