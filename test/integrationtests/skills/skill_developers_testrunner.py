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
"""Find test files starting from the directory where this file resides.

The skill_developers_testrunner.py is intended to be copied to the
skill developers own directory, where the skills __init__.py file
resides. Running the python unit test in this module from that file
location, will test the skill developers test the same way as
discover_test.py, but running only the skill developers test.
It is executed as a unit test.

"""

import glob
import unittest
import os
from test.integrationtests.skills.skill_tester import MockSkillsLoader
from test.integrationtests.skills.skill_tester import SkillTest

HOME_DIR = os.path.dirname(os.path.abspath(__file__))


def discover_tests():
    """Find skills whith test files

    For all skills with test files, starten from current directory,
    find the test files in subdirectory test/intent.

    :return: skills and corresponding test case files found
    """

    tests = {}

    skills = [HOME_DIR]

    for skill in skills:
        test_intent_files = [
            f for f
            in glob.glob(os.path.join(skill, 'test/intent/*.intent.json'))
        ]
        if len(test_intent_files) > 0:
            tests[skill] = test_intent_files

    return tests


class IntentTestSequenceMeta(type):
    def __new__(mcs, name, bases, d):
        def gen_test(a, b):
            def test(self):
                if not SkillTest(a, b, self.emitter).run(self.loader):
                    assert False
            return test

        tests = discover_tests()
        for skill in tests.keys():
            skill_name = os.path.basename(skill)  # Path of the skill
            for example in tests[skill]:
                # Name of the intent
                example_name = os.path.basename(
                    os.path.splitext(os.path.splitext(example)[0])[0])
                test_name = "test_IntentValidation[%s:%s]" % (skill_name,
                                                              example_name)
                d[test_name] = gen_test(skill, example)
        return type.__new__(mcs, name, bases, d)


class IntentTestSequence(unittest.TestCase):
    """This is the TestCase class that pythons unit tester can execute.
    """
    __metaclass__ = IntentTestSequenceMeta
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
