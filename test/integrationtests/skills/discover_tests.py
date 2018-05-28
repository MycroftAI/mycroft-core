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
from os.path import exists, join, expanduser
import sys
import imp

from mycroft.configuration import Configuration
from test.integrationtests.skills.skill_tester import MockSkillsLoader
from test.integrationtests.skills.skill_tester import SkillTest


def discover_tests(skills_dir):
    """ Find all tests for the skills in the default skill path,
    or in the path provided as the LAST command line argument.

    Finds intent test json files and corresponding .../test/__init__.py
    containing a test_runner function allowing per skill mocking.

    Returns:
        Tests, lists of (intent example, test environment)
    """
    tests = {}
    skills = [
        skill for skill
        in sorted(glob.glob(skills_dir + '/*'))
        if os.path.isdir(skill)
    ]

    for skill in skills:
        # Load test environment file
        test_env = None
        if exists(os.path.join(skill, 'test/__init__.py')):
            module = imp.load_source(skill + '.test_env',
                                     os.path.join(skill, 'test/__init__.py'))
            if hasattr(module, 'test_runner') and callable(module.test_runner):
                test_env = module

        # Find all intent test files
        test_intent_files = [
            (f, test_env) for f
            in sorted(
                glob.glob(os.path.join(skill, 'test/intent/*.intent.json')))
        ]
        if len(test_intent_files) > 0:
            tests[skill] = test_intent_files

    return tests


def get_skills_dir():
    if len(sys.argv) > 1:
        return expanduser(sys.argv[-1])

    return expanduser(join(Configuration.get()['data_dir'],
                      Configuration.get()['skills']['msm']['directory']))


skills_dir = get_skills_dir()
tests = discover_tests(skills_dir)
loader = MockSkillsLoader(skills_dir)
emitter = loader.load_skills()


class TestCase(object):
    @pytest.mark.parametrize("skill,test", sum([
        [(skill, test) for test in tests[skill]]
        for skill in tests.keys()
        ], []))
    def test_skill(self, skill, test):
        example, test_env = test
        if test_env:
            assert test_env.test_runner(skill, example, emitter, loader)
        else:
            assert SkillTest(skill, example, emitter).run(loader)
