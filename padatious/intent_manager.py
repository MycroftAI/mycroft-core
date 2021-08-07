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

from padatious.intent import Intent
from padatious.match_data import MatchData
from padatious.training_manager import TrainingManager
from padatious.util import tokenize


class IntentManager(TrainingManager):
    def __init__(self, cache):
        super(IntentManager, self).__init__(Intent, cache)

    def calc_intents(self, query, entity_manager):
        sent = tokenize(query)
        matches = []
        for i in self.objects:
            match = i.match(sent, entity_manager)
            match.detokenize()
            matches.append(match)
        return matches
