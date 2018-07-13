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
import argparse
from test.integrationtests.skills.skill_tester import MockSkillsLoader
from test.integrationtests.skills.skill_tester import SkillTest


help = "Standalone test utility for Mycroft Skills.  This will execute the " \
    "tests defined under the Skill's test/intent folder.  For more " \
    "information on creating tests, see:  " \
    "https://mycroft.ai/documentation/skills/automatic-testing/"

# Get path to skill(s) to test from command line, default to cwd
parser = argparse.ArgumentParser(description=help)
parser.add_argument("skill_path", nargs='?', default=os.getcwd(),
                    help="path to skill to test, default=current")
args = parser.parse_args()
HOME_DIR = args.skill_path


def discover_tests():
    """Find skills with test files

    For all skills with test files, starten from current directory,
    find the test files in subdirectory test/intent.

    :return: skills and corresponding test case files found
    """
    tests = {}

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

    return tests


class IntentTestSequenceMeta(type):
    def __new__(mcs, name, bases, d):
        def gen_test(a, b):
            def test(self):
                t = SkillTest(a, b, self.emitter)
                if not t.run(self.loader):
                    assert False, "Failure: " + t.failure_msg
            return test

        tests = discover_tests()
        for skill in tests.keys():
            skill_name = os.path.basename(skill)  # Path of the skill
            for example in tests[skill]:
                # Name of the intent
                test_filename = os.path.basename(example)
                test_name = "test_Intent[%s:%s]" % (skill_name,
                                                    test_filename)
                d[test_name] = gen_test(skill, example)
        return type.__new__(mcs, name, bases, d)


class IntentTestSequence(unittest.TestCase, metaclass=IntentTestSequenceMeta):
    """This is the TestCase class that Python's unit tester can execute.
    """
    loader = None

    @classmethod
    def setUpClass(cls):
        cls.loader = MockSkillsLoader(HOME_DIR)
        cls.emitter = cls.loader.load_skills()

    @classmethod
    def tearDownClass(cls):
        cls.loader.unload_skills()


if __name__ == '__main__':
    unittest.main()
