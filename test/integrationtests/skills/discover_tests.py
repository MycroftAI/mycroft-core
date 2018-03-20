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
import pytest

import glob
import os
import sys

from test.integrationtests.skills.skill_tester import MockSkillsLoader
from test.integrationtests.skills.skill_tester import SkillTest

SKILL_PATH = '/opt/mycroft/skills/'


def discover_tests():
    global SKILL_PATH
    if len(sys.argv) > 2:
        SKILL_PATH = sys.argv.pop()
    tests = {}
    skills = [
        skill for skill
        in glob.glob(SKILL_PATH + '/*')
        if os.path.isdir(skill)
    ]

    for skill in skills:
        test_intent_files = [
            f for f
            in glob.glob(os.path.join(skill, 'test/intent/*.intent.json'))
        ]
        if len(test_intent_files) > 0:
            tests[skill] = test_intent_files

    return tests


tests = discover_tests()
loader = MockSkillsLoader(SKILL_PATH)
emitter = loader.load_skills()


class TestCase(object):
    @pytest.mark.parametrize("skill,example", sum([
        [(skill, example) for example in tests[skill]]
        for skill in tests.keys()
        ], []))
    def test_skill(self, skill, example):
        assert SkillTest(skill, example, emitter).run(loader)
