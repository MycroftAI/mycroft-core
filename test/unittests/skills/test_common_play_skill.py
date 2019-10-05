# -*- coding: utf-8 -*-
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
import sys
import unittest

from unittest.mock import MagicMock, patch
from adapt.intent import IntentBuilder
from os.path import join, dirname, abspath
from re import error
from datetime import datetime
import json

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.skills.skill_data import (load_regex_from_file, load_regex,
                                       load_vocabulary, read_vocab_file)
from mycroft.skills.core import MycroftSkill, resting_screen_handler
from mycroft.skills.intent_service import open_intent_envelope
from mycroft.skills.common_play_skill import bind, CPS_play, CPS_match_query_phrase

class CommonPlayTest(CommonPlaySkill):
    def CPS_match_query_phrase(self, phrase):
        return None

    def CPS_start(self, phrase, data):
        pass
        
class TestCommonPlaySkill(unittest.TestCase):
    def test_bind(self):
        skill = CommonPlayTest()
        bus = Mock()
        skill.bind(bus)
