import os
import sys
import glob
import unittest
from test.integrationtests.skills.skill_tester import MockSkillsLoader
from test.integrationtests.skills.skill_tester import SkillTest

__author__ = 'seanfitz'

SKILL_PATH = '/opt/mycroft/skills'


def discover_tests():
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

    return tests


class IntentTestSequenceMeta(type):
    def __new__(mcs, name, bases, d):
        def gen_test(a, b):
            def test(self):
                SkillTest(a, b, self.emitter).run(self.loader)
            return test

        tests = discover_tests()
        for skill in tests.keys():
            skill_name = os.path.basename(skill)
            for example in tests[skill]:
                example_name = os.path.basename(
                    os.path.splitext(os.path.splitext(example)[0])[0])
                test_name = "test_IntentValidation[%s:%s]" % (skill_name,
                                                              example_name)
                d[test_name] = gen_test(skill, example)
        return type.__new__(mcs, name, bases, d)


class IntentTestSequence(unittest.TestCase):
    __metaclass__ = IntentTestSequenceMeta

    @classmethod
    def setUpClass(self):
        self.loader = MockSkillsLoader(SKILL_PATH)
        self.emitter = self.loader.load_skills()

    @classmethod
    def tearDownClass(self):
        self.loader.unload_skills()


if __name__ == '__main__':
    unittest.main()
