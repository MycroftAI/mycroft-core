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

from padatious.entity import Entity
from padatious.training_manager import TrainingManager


class EntityManager(TrainingManager):
    def __init__(self, cache):
        super(EntityManager, self).__init__(Entity, cache)
        self.entity_dict = {}

    def calc_ent_dict(self):
        for i in self.objects:
            self.entity_dict[i.name] = i

    def find(self, intent_name, token):
        local_name, global_name = '', token
        if ':' in intent_name:
            local_name = intent_name.split(':')[0] + ':' + token
        return self.entity_dict.get(local_name, self.entity_dict.get(global_name))

    def remove(self, name):
        name = '{' + name + '}'
        if name in self.entity_dict:
            del self.entity_dict[name]
        super(EntityManager, self).remove(name)
