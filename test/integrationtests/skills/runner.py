# Copyright 2018 Mycroft AI Inc.
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
"""Execute Mycroft Skill intent testing

This standalone tester can be invoked by a skill developer from
within the Mycroft venv by using the command:
    python -m test.integrationtests.skills.runner
This will test the skill the same way as discover_test.py used
for automatic integration tests, but will run only the skill
developer's tests.
"""

import glob
import unittest
import os
from os.path import exists
import sys
import importlib
import argparse
from test.integrationtests.skills.skill_tester import MockSkillsLoader
from test.integrationtests.skills.skill_tester import SkillTest


desc = "Standalone test utility for Mycroft Skills.  This will execute the " \
    "tests defined under the Skill's test/intent folder.  For more " \
    "information on creating tests, see:  " \
    "https://mycroft.ai/documentation/skills/automatic-testing/"

# Get path to skill(s) to test from command line, default to cwd
parser = argparse.ArgumentParser(description=desc)
parser.add_argument("skill_path", nargs='?', default=os.getcwd(),
                    help="path to skill to test, default=current")
args = parser.parse_args()
HOME_DIR = os.path.dirname(args.skill_path + '/')
sys.argv = sys.argv[:1]


def load_test_environment(skill):
    """Load skill's test environment if present

    Args:
        skill (str): path to skill root folder

    Returns:
        Module if a valid test environment module was found else None
    """
    test_env = None
    test_env_path = os.path.join(skill, 'test/__init__.py')
    if exists(test_env_path):
        skill_env = skill + '.test_env'
        spec = importlib.util.spec_from_file_location(skill_env, test_env_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[skill_env] = module
        spec.loader.exec_module(module)
        if (hasattr(module, 'test_runner') and
                callable(module.test_runner) or
                hasattr(module, 'test_setup') and
                callable(module.test_setup)):
            test_env = module
    return test_env


def discover_tests():
    """Find skills with test files

    For all skills with test files, starten from current directory,
    find the test files in subdirectory test/intent.

    Returns:
        Test case files found along with test environment script if available.
    """

    tests = {}
    test_envs = {}

    skills = [HOME_DIR]

    for skill in skills:
        print("Searching for tests under: " +
              os.path.join(skill, "test/intent/*.json"))
        test_intent_files = [
            f for f
            in sorted(
                glob.glob(os.path.join(skill, 'test/intent/*.json')))
        ]
        if len(test_intent_files) > 0:
            tests[skill] = test_intent_files

        # Load test environment script
        test_env = load_test_environment(skill)
        test_envs[skill] = test_env

    return tests, test_envs


class IntentTestSequenceMeta(type):
    def __new__(mcs, name, bases, d):
        def gen_test(a, b, test_env):
            def test(self):
                t = SkillTest(a, b, self.emitter)
                if not t.run(self.loader):
                    assert False, "Failure: " + t.failure_msg

            def test_env_test(self):
                assert test_env.test_runner(a, b, self.emitter, self.loader)

            if test_env and hasattr(test_env, 'test_runner'):
                return test_env_test
            else:
                return test
        tests, test_envs = discover_tests()
        mcs.tests, mcs.test_envs = tests, test_envs

        for skill in tests.keys():
            skill_name = os.path.basename(skill)  # Path of the skill
            for example in tests[skill]:
                # Name of the intent
                test_filename = os.path.basename(example)
                test_name = "test_Intent[%s:%s]" % (skill_name,
                                                    test_filename)
                test_env = test_envs[skill]
                d[test_name] = gen_test(skill, example, test_env)

        return type.__new__(mcs, name, bases, d)


class IntentTestSequence(unittest.TestCase, metaclass=IntentTestSequenceMeta):
    """This is the TestCase class that Python's unit tester can execute.
    """
    loader = None

    @classmethod
    def setUpClass(cls):
        cls.loader = MockSkillsLoader(HOME_DIR)
        cls.emitter = cls.loader.load_skills()

        # Run test setup provided by the test environment
        for s in cls.loader.skills:
            if (s.root_dir in cls.test_envs and
                    hasattr(cls.test_envs[s.root_dir], 'test_setup')):
                try:
                    cls.test_envs[s.root_dir].test_setup(s)
                except Exception as e:
                    print('test_setup for {} failed: {}'.format(s.name,
                                                                repr(e)))

    @classmethod
    def tearDownClass(cls):
        cls.loader.unload_skills()


if __name__ == '__main__':
    unittest.main()
