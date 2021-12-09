# Copyright 2017 Mycroft AI Inc.
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
from adapt.intent import IntentBuilder

from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler, intent_file_handler


class TestSkill(MycroftSkill):
    """ Test skill for intent_handler decorator. """
    @intent_handler(IntentBuilder('a').require('Keyword').build())
    def handler(self, message):
        pass

    @intent_file_handler('test.intent')
    def handler2(self, message):
        pass

    def stop(self):
        pass
