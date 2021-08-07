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

from os.path import join

from padatious.simple_intent import SimpleIntent
from padatious.trainable import Trainable


class Entity(SimpleIntent, Trainable):
    def __init__(self, name, *args, **kwargs):
        SimpleIntent.__init__(self, name)
        Trainable.__init__(self, name, *args, **kwargs)

    @staticmethod
    def verify_name(token):
        if token[0] in '{}' or token[-1] in '{}':
            raise ValueError('token must not be surrounded in braces (ie. {word} should be word)')

    @staticmethod
    def wrap_name(name):
        """Wraps SkillName:entity into SkillName:{entity}"""
        if ':' in name:
            parts = name.split(':')
            intent_name, ent_name = parts[0], parts[1:]
            return intent_name + ':{' + ':'.join(ent_name) + '}'
        else:
            return '{' + name + '}'

    def save(self, folder):
        prefix = join(folder, self.name)
        SimpleIntent.save(self, prefix)
        self.save_hash(prefix)

    @classmethod
    def from_file(cls, name, folder):
        self = super(Entity, cls).from_file(name, join(folder, name))
        self.load_hash(join(folder, name))
        return self
