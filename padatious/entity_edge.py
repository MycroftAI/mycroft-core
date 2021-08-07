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

from fann2 import libfann as fann

from padatious.id_manager import IdManager
from padatious.util import StrEnum, resolve_conflicts


class Ids(StrEnum):
    end = ':end'


class EntityEdge(object):
    """
    Represents the left or right side of an entity (a PosIntent)

    Args:
        direction (int): -1 for left and +1 for right
        token (str): token to attach to (something like {word})
        intent_name (str): name of parent intent
    """
    def __init__(self,  direction, token, intent_name):
        self.ids = IdManager(Ids)
        self.intent_name = intent_name
        self.token = token
        self.dir = direction
        self.net = None

    def get_end(self, sent):
        return len(sent) if self.dir > 0 else -1

    def vectorize(self, sent, pos):
        unknown = 0
        vector = self.ids.vector()
        end_pos = self.get_end(sent)
        for i in range(pos + self.dir, end_pos, self.dir):
            if sent[i] in self.ids:
                self.ids.assign(vector, sent[i], 1.0 / abs(i - pos))
            else:
                unknown += 1
        self.ids.assign(vector, Ids.end, 1.0 / abs(end_pos - pos))
        return vector

    def match(self, sent, pos):
        return self.net.run(self.vectorize(sent, pos))[0]

    def configure_net(self):
        layers = [len(self.ids), 3, 1]

        self.net = fann.neural_net()
        self.net.create_standard_array(layers)
        self.net.set_activation_function_hidden(fann.SIGMOID_SYMMETRIC_STEPWISE)
        self.net.set_activation_function_output(fann.SIGMOID_STEPWISE)
        self.net.set_train_stop_function(fann.STOPFUNC_BIT)
        self.net.set_bit_fail_limit(0.1)

    def save(self, prefix):
        prefix += '.' + {-1: 'l', +1: 'r'}[self.dir]
        self.net.save(str(prefix + '.net'))  # Must have str()
        self.ids.save(prefix)

    def load(self, prefix):
        prefix += '.' + {-1: 'l', +1: 'r'}[self.dir]
        self.net = fann.neural_net()
        if not self.net.create_from_file(str(prefix + '.net')):  # Must have str()
            raise FileNotFoundError(str(prefix + '.net'))
        self.ids.load(prefix)

    def train(self, train_data):
        for sent in train_data.my_sents(self.intent_name):
            if self.token in sent:
                for i in range(sent.index(self.token) + self.dir,
                               self.get_end(sent), self.dir):
                    if sent[i][0] != '{':
                        self.ids.add_token(sent[i])

        inputs, outputs = [], []

        def pollute(sent, i, out_val):
            """Simulates multiple token words in adjacent entities"""
            for j, check_token in enumerate(sent):
                d = j - i
                if int(d > 0) - int(d < 0) == self.dir and check_token.startswith('{'):
                    for pol_len in range(1, 4):
                        s = sent[:j] + [':0'] * pol_len + sent[j + 1:]
                        p = i + (pol_len - 1) * int(self.dir < 0)
                        inputs.append(self.vectorize(s, p))
                        outputs.append([out_val])

        def add_sents(sents, out_fn):
            for sent in sents:
                for i, token in enumerate(sent):
                    out_val = out_fn(token)
                    inputs.append(self.vectorize(sent, i))
                    outputs.append([out_val])
                    if out_val == 1.0:
                        pollute(sent, i, 1.0)

        add_sents(train_data.my_sents(self.intent_name), lambda x: float(x == self.token))
        add_sents(train_data.other_sents(self.intent_name), lambda x: 0.0)
        inputs, outputs = resolve_conflicts(inputs, outputs)

        data = fann.training_data()
        data.set_train_data(inputs, outputs)

        for _ in range(10):
            self.configure_net()
            self.net.train_on_data(data, 1000, 0, 0)
            self.net.test_data(data)
            if self.net.get_bit_fail() == 0:
                break
