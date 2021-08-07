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

from abc import ABCMeta, abstractmethod


class Trainable(object):
    __metaclass__ = ABCMeta

    def __init__(self, name, hsh=b''):
        self.name = name
        self.hash = hsh

    def load_hash(self, prefix):
        with open(prefix + '.hash', 'rb') as f:
            self.hash = f.read()

    def save_hash(self, prefix):
        with open(prefix + '.hash', 'wb') as f:
            f.write(self.hash)

    @abstractmethod
    def train(self, data):
        pass

    @abstractmethod
    def save(self, prefix):
        pass

    @classmethod
    @abstractmethod
    def from_file(self, name, folder):
        pass
