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

import json
import math
from os.path import join

from padatious.match_data import MatchData
from padatious.pos_intent import PosIntent
from padatious.simple_intent import SimpleIntent
from padatious.trainable import Trainable


class Intent(Trainable):
    """Full intent object to handle entity extraction and intent matching"""

    def __init__(self, *args, **kwargs):
        super(Intent, self).__init__(*args, **kwargs)
        self.simple_intent = SimpleIntent(self.name)
        self.pos_intents = []

    def match(self, sent, entities=None):
        possible_matches = [MatchData(self.name, sent)]
        for pi in self.pos_intents:
            entity = entities.find(self.name, pi.token) if entities else None
            for i in list(possible_matches):
                possible_matches += pi.match(i, entity)

        possible_matches = [i for i in possible_matches if i.conf >= 0.0]

        for i in possible_matches:
            conf = ((i.conf / len(i.matches)) if len(i.matches) > 0 else 0) + 0.5
            i.conf = math.sqrt(conf * self.simple_intent.match(i.sent))

        return max(possible_matches, key=lambda x: x.conf)

    def save(self, folder):
        prefix = join(folder, self.name)
        with open(prefix + '.hash', 'wb') as f:
            f.write(self.hash)
        self.simple_intent.save(prefix)
        prefix += '.pos'
        with open(prefix, 'w') as f:
            json.dump([i.token for i in self.pos_intents], f)
        for pos_intent in self.pos_intents:
            pos_intent.save(prefix)

    @classmethod
    def from_file(cls, name, folder):
        self = cls(name)
        prefix = join(folder, name)
        self.load_hash(prefix)
        self.simple_intent = SimpleIntent.from_file(name, prefix)
        prefix += '.pos'
        with open(prefix, 'r') as f:
            tokens = json.load(f)
        for token in tokens:
            self.pos_intents.append(PosIntent.from_file(prefix, token))
        return self

    def train(self, train_data):
        tokens = set([token for sent in train_data.my_sents(self.name)
                      for token in sent if token.startswith('{')])
        self.pos_intents = [PosIntent(i, self.name) for i in tokens]

        self.simple_intent.train(train_data)
        for i in self.pos_intents:
            i.train(train_data)
