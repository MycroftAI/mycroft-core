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

from padatious.util import StrEnum


class IdManager(object):
    """
    Gives manages specific unique identifiers for tokens.
    Used to convert tokens to vectors
    """
    def __init__(self, id_cls=StrEnum, ids=None):
        if ids is not None:
            self.ids = ids
        else:
            self.ids = {}
            for i in id_cls.values():
                self.add_token(i)

    def __len__(self):
        return len(self.ids)

    @staticmethod
    def adj_token(token):
        if token.isdigit():
            for i in range(10):
                if str(i) in token:
                    token = token.replace(str(i), '#')
        return token

    def vector(self):
        return [0.0] * len(self.ids)

    def save(self, prefix):
        with open(prefix + '.ids', 'w') as f:
            json.dump(self.ids, f)

    def load(self, prefix):
        with open(prefix + '.ids', 'r') as f:
            self.ids = json.load(f)

    def assign(self, vector, key, val):
        vector[self.ids[self.adj_token(key)]] = val

    def __contains__(self, token):
        return self.adj_token(token) in self.ids

    def add_token(self, token):
        token = self.adj_token(token)
        if token not in self.ids:
            self.ids[token] = len(self.ids)

    def add_sent(self, sent):
        for token in sent:
            self.add_token(token)
