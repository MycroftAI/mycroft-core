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
from padatious.util import resolve_conflicts, StrEnum


class Ids(StrEnum):
    unknown_tokens = ':0'
    w_1 = ':1'
    w_2 = ':2'
    w_3 = ':3'
    w_4 = ':4'


class SimpleIntent(object):
    """General intent used to match sentences or phrases"""
    LENIENCE = 0.6

    def __init__(self, name=''):
        self.name = name
        self.ids = IdManager(Ids)
        self.net = None  # type: fann.neural_net

    def match(self, sent):
        return max(0, self.net.run(self.vectorize(sent))[0])

    def vectorize(self, sent):
        vector = self.ids.vector()
        unknown = 0
        for token in sent:
            if token in self.ids:
                self.ids.assign(vector, token, 1.0)
            else:
                unknown += 1
        if len(sent) > 0:
            self.ids.assign(vector, Ids.unknown_tokens, unknown / float(len(sent)))
            self.ids.assign(vector, Ids.w_1, len(sent) / 1)
            self.ids.assign(vector, Ids.w_2, len(sent) / 2.)
            self.ids.assign(vector, Ids.w_3, len(sent) / 3.)
            self.ids.assign(vector, Ids.w_4, len(sent) / 4.)
        return vector

    def configure_net(self):
        self.net = fann.neural_net()
        self.net.create_standard_array([len(self.ids), 10, 1])
        self.net.set_activation_function_hidden(fann.SIGMOID_SYMMETRIC_STEPWISE)
        self.net.set_activation_function_output(fann.SIGMOID_SYMMETRIC_STEPWISE)
        self.net.set_train_stop_function(fann.STOPFUNC_BIT)
        self.net.set_bit_fail_limit(0.1)

    def train(self, train_data):
        for sent in train_data.my_sents(self.name):
            self.ids.add_sent(sent)

        inputs = []
        outputs = []

        def add(vec, out):
            inputs.append(self.vectorize(vec))
            outputs.append([out])

        def pollute(sent, p):
            sent = sent[:]
            for _ in range(int((len(sent) + 2) / 3)):
                sent.insert(p, ':null:')
            add(sent, self.LENIENCE)

        def weight(sent):
            def calc_weight(w): return pow(len(w), 3.0)
            total_weight = 0.0
            for word in sent:
                total_weight += calc_weight(word)
            for word in sent:
                weight = 0 if word.startswith('{') else calc_weight(word)
                add([word], weight / total_weight)

        for sent in train_data.my_sents(self.name):
            add(sent, 1.0)
            weight(sent)

            # Generate samples with extra unknown tokens unless
            # the sentence is supposed to allow unknown tokens via the special :0
            if not any(word[0] == ':' and word != ':' for word in sent):
                pollute(sent, 0)
                pollute(sent, len(sent))

        for sent in train_data.other_sents(self.name):
            add(sent, 0.0)
        add([':null:'], 0.0)
        add([], 0.0)

        for sent in train_data.my_sents(self.name):
            without_entities = sent[:]
            for i, token in enumerate(without_entities):
                if token.startswith('{'):
                    without_entities[i] = ':null:'
            if without_entities != sent:
                add(without_entities, 0.0)

        inputs, outputs = resolve_conflicts(inputs, outputs)

        train_data = fann.training_data()
        train_data.set_train_data(inputs, outputs)

        for _ in range(10):
            self.configure_net()
            self.net.train_on_data(train_data, 1000, 0, 0)
            self.net.test_data(train_data)
            if self.net.get_bit_fail() == 0:
                break

    def save(self, prefix):
        prefix += '.intent'
        self.net.save(str(prefix + '.net'))  # Must have str()
        self.ids.save(prefix)

    @classmethod
    def from_file(cls, name, prefix):
        prefix += '.intent'
        self = cls(name)
        self.net = fann.neural_net()
        if not self.net.create_from_file(str(prefix + '.net')):  # Must have str()
            raise FileNotFoundError(str(prefix + '.net'))
        self.ids.load(prefix)
        return self
