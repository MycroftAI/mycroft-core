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
"""This module is used for testing all skills at the skill level.

    Because the module operate on skill level, it runs not only all the intent
    tests, it also find out if all intents in a skill are tested, i.e. if any
    test cases are missing. It print a list of missing test cases for each
    skill, and fails if it finds any. It is executed as a unit test.
"""

import glob
import sys
import unittest
import os
from test.integrationtests.skills.skill_tester import MockSkillsLoader
from test.integrationtests.skills.skill_tester import SkillTest

SKILL_PATH = '/opt/mycroft/skills'


def all_tests():
    """Find skills and test files

    For all skills on SKILL_PATH, find the test files in subdirectory
    test/intent. Return an empty list of test files for skills without any
    test files

    :return: all skills and corresponding test case files found
    """

    global SKILL_PATH
    if len(sys.argv) > 1:
        SKILL_PATH = sys.argv.pop(1)
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
        else:
            tests[skill] = []

    return tests


class SkillTestStatus(object):
    """Hold the intents of a skill, and the test status

        Contents are created during test
    """
    def __init__(self):
        self.intent_list = {}

    def append_intent(self, skill):
        for i in skill.registered_intents:
            if not i[0] in self.intent_list:
                self.intent_list.update({i[0]: False})

    def set_tested(self, intent_name):
        self.intent_list.update({intent_name: True})


class IntentTestSequenceMeta(type):
    """Metaclass to create test case for each skill

    """
    def __new__(mcs, name, bases, d):
        def gen_test(skill):
            def test(self):
                skill_test_status = SkillTestStatus()
                skill_name = os.path.basename(skill)  # Path of the skill
                if len(tests[skill]):
                    succeeded = False
                    for test_case in tests[skill]:
                        if SkillTest(skill, test_case, self.emitter,
                                     test_status=skill_test_status). \
                                run(self.loader):
                            succeeded = True

                    untested = [i
                                for i in skill_test_status.intent_list.items()
                                if not all(i)]
                    for intent_status in untested:
                        print "No test found for intent: " + intent_status[0]

                    if len(untested) > 0 or not succeeded:
                        assert False

                else:
                    print "No tests found for " + skill_name
                    assert False

            return test

        tests = all_tests()
        for skill in tests.keys():
            test_name = "test_skill[%s]" % (os.path.basename(skill))
            d[test_name] = gen_test(skill)

        return type.__new__(mcs, name, bases, d)


class IntentTestSequence(unittest.TestCase):
    __metaclass__ = IntentTestSequenceMeta
    loader = None

    @classmethod
    def setUpClass(cls):
        cls.loader = MockSkillsLoader(SKILL_PATH)
        cls.emitter = cls.loader.load_skills()

    @classmethod
    def tearDownClass(cls):
        cls.loader.unload_skills()


if __name__ == '__main__':
    unittest.main()
