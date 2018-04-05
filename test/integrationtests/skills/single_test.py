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
""" Test a single skill

    python single_test.py PATH_TO_SKILL
"""

import glob
import unittest
import os
from os.path import exists
import imp

from test.integrationtests.skills.skill_tester import MockSkillsLoader
from test.integrationtests.skills.skill_tester import SkillTest

import sys

d = sys.argv.pop() + '/'
SKILL_DIR = os.path.dirname(d)


def discover_tests():
    """Find skill withh test files.

    For all skills with test files, starten from current directory,
    find the test files in subdirectory test/intent.

    Returns:
        Test case files found along with test environment script if available.
    """

    tests = {}
    test_envs = {}

    skills = [SKILL_DIR]

    for skill in skills:
        # Find intent tests
        test_intent_files = [
            f for f
            in glob.glob(os.path.join(skill, 'test/intent/*.intent.json'))
        ]
        if len(test_intent_files) > 0:
            tests[skill] = test_intent_files

        # Load test environment script
        test_env = None
        if exists(os.path.join(skill, 'test/__init__.py')):
            module = imp.load_source(skill + '.test_env',
                                     os.path.join(skill, 'test/__init__.py'))
            if hasattr(module, 'test_runner') and callable(module.test_runner):
                test_env = module
        test_envs[skill] = test_env

    return tests, test_envs


class IntentTestSequenceMeta(type):
    def __new__(mcs, name, bases, d):
        def gen_test(a, b, test_env):
            def test(self):
                assert SkillTest(a, b, self.emitter).run(self.loader)

            def test_env_test(self):
                assert test_env.test_runner(a, b, self.emitter, self.loader)

            if test_env_test:
                return test_env_test
            else:
                return test

        tests, test_envs = discover_tests()
        for skill in tests.keys():
            skill_name = os.path.basename(skill)  # Path of the skill
            for example in tests[skill]:
                # Name of the intent
                example_name = os.path.basename(
                    os.path.splitext(os.path.splitext(example)[0])[0])
                test_name = "test_IntentValidation[%s:%s]" % (skill_name,
                                                              example_name)
                test_env = test_envs[skill]
                d[test_name] = gen_test(skill, example, test_env)

        return type.__new__(mcs, name, bases, d)


class IntentTestSequence(unittest.TestCase):
    """This is the TestCase class that pythons unit tester can execute.
    """
    __metaclass__ = IntentTestSequenceMeta
    loader = None

    @classmethod
    def setUpClass(cls):
        cls.loader = MockSkillsLoader(SKILL_DIR)
        cls.emitter = cls.loader.load_skills()

    @classmethod
    def tearDownClass(cls):
        cls.loader.unload_skills()


if __name__ == '__main__':
    unittest.main()
