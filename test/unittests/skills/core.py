import unittest
import sys
from os.path import join, dirname, abspath
from re import error

from mycroft.skills.core import load_regex_from_file, load_regex, \
    load_vocab_from_file, load_vocabulary, MycroftSkill, \
    load_skill, create_skill_descriptor
from adapt.intent import IntentBuilder

from mycroft.util.log import getLogger

__author__ = 'eward'
logger = getLogger(__name__)


class MockEmitter(object):
    def __init__(self):
        self.reset()

    def emit(self, message):
        self.types.append(message.type)
        self.results.append(message.data)

    def get_types(self):
        return self.types

    def get_results(self):
        return self.results

    def on(self, event, f):
        pass

    def reset(self):
        self.types = []
        self.results = []


class MycroftSkillTest(unittest.TestCase):
    emitter = MockEmitter()
    regex_path = abspath(join(dirname(__file__), '../regex_test'))
    vocab_path = abspath(join(dirname(__file__), '../vocab_test'))

    def setUp(self):
        self.emitter.reset()

    def check_vocab_from_file(self, filename, vocab_type=None, result_list=[]):
        load_vocab_from_file(join(self.vocab_path, filename), vocab_type,
                             self.emitter)
        self.check_emitter(result_list)

    def check_regex_from_file(self, filename, result_list=[]):
        load_regex_from_file(join(self.regex_path, filename), self.emitter)
        self.check_emitter(result_list)

    def check_vocab(self, path, result_list=[]):
        load_vocabulary(path, self.emitter)
        self.check_emitter(result_list)

    def check_regex(self, path, result_list=[]):
        load_regex(path, self.emitter)
        self.check_emitter(result_list)

    def check_emitter(self, result_list):
        for type in self.emitter.get_types():
            self.assertEquals(type, 'register_vocab')
        self.assertEquals(sorted(self.emitter.get_results()),
                          sorted(result_list))
        self.emitter.reset()

    def test_load_regex_from_file_single(self):
        self.check_regex_from_file('valid/single.rx',
                                   [{'regex': '(?P<SingleTest>.*)'}])

    def test_load_regex_from_file_multiple(self):
        self.check_regex_from_file('valid/multiple.rx',
                                   [{'regex': '(?P<MultipleTest1>.*)'},
                                    {'regex': '(?P<MultipleTest2>.*)'}])

    def test_load_regex_from_file_none(self):
        self.check_regex_from_file('invalid/none.rx')

    def test_load_regex_from_file_invalid(self):
        try:
            self.check_regex_from_file('invalid/invalid.rx')
        except error as e:
            self.assertEquals(e.__str__(),
                              'unexpected end of regular expression')

    def test_load_regex_from_file_does_not_exist(self):
        try:
            self.check_regex_from_file('does_not_exist.rx')
        except IOError as e:
            self.assertEquals(e.strerror, 'No such file or directory')

    def test_load_regex_full(self):
        self.check_regex(join(self.regex_path, 'valid'),
                         [{'regex': '(?P<MultipleTest1>.*)'},
                          {'regex': '(?P<MultipleTest2>.*)'},
                          {'regex': '(?P<SingleTest>.*)'}])

    def test_load_regex_empty(self):
        self.check_regex(join(dirname(__file__),
                              'empty_dir'))

    def test_load_regex_fail(self):
        try:
            self.check_regex(join(dirname(__file__),
                                  'regex_test_fail'))
        except OSError as e:
            self.assertEquals(e.strerror, 'No such file or directory')

    def test_load_vocab_from_file_single(self):
        self.check_vocab_from_file('valid/single.voc', 'test_type',
                                   [{'start': 'test', 'end': 'test_type'}])

    def test_load_vocab_from_file_single_alias(self):
        self.check_vocab_from_file('valid/singlealias.voc', 'test_type',
                                   [{'start': 'water', 'end': 'test_type'},
                                    {'start': 'watering', 'end': 'test_type',
                                     'alias_of': 'water'}])

    def test_load_vocab_from_file_multiple(self):
        self.check_vocab_from_file('valid/multiple.voc', 'test_type',
                                   [{'start': 'animal', 'end': 'test_type'},
                                    {'start': 'animals', 'end': 'test_type'}])

    def test_load_vocab_from_file_multiple_alias(self):
        self.check_vocab_from_file('valid/multiplealias.voc', 'test_type',
                                   [{'start': 'chair', 'end': 'test_type'},
                                    {'start': 'chairs', 'end': 'test_type',
                                     'alias_of': 'chair'},
                                    {'start': 'table', 'end': 'test_type'},
                                    {'start': 'tables', 'end': 'test_type',
                                     'alias_of': 'table'}])

    def test_load_vocab_from_file_none(self):
        self.check_vocab_from_file('none.voc')

    def test_load_vocab_from_file_does_not_exist(self):
        try:
            self.check_vocab_from_file('does_not_exist.voc')
        except IOError as e:
            self.assertEquals(e.strerror, 'No such file or directory')

    def test_load_vocab_full(self):
        self.check_vocab(join(self.vocab_path, 'valid'),
                         [{'start': 'test', 'end': 'single'},
                          {'start': 'water', 'end': 'singlealias'},
                          {'start': 'watering', 'end': 'singlealias',
                           'alias_of': 'water'},
                          {'start': 'animal', 'end': 'multiple'},
                          {'start': 'animals', 'end': 'multiple'},
                          {'start': 'chair', 'end': 'multiplealias'},
                          {'start': 'chairs', 'end': 'multiplealias',
                           'alias_of': 'chair'},
                          {'start': 'table', 'end': 'multiplealias'},
                          {'start': 'tables', 'end': 'multiplealias',
                           'alias_of': 'table'}])

    def test_load_vocab_empty(self):
        self.check_vocab(join(dirname(__file__), 'empty_dir'))

    def test_load_vocab_fail(self):
        try:
            self.check_regex(join(dirname(__file__),
                                  'vocab_test_fail'))
        except OSError as e:
            self.assertEquals(e.strerror, 'No such file or directory')

    def test_load_skill(self):
        """ Verify skill load function. """
        e_path = join(dirname(__file__), 'test_skill')
        s = load_skill(create_skill_descriptor(e_path), MockEmitter(), 847)
        self.assertEquals(s._dir, e_path)
        self.assertEquals(s.skill_id, 847)
        self.assertEquals(s.name, 'LoadTestSkill')

    def check_register_intent(self, result_list):
        for type in self.emitter.get_types():
            self.assertEquals(type, 'register_intent')
        self.assertEquals(sorted(self.emitter.get_results()),
                          sorted(result_list))
        self.emitter.reset()

    def test_register_intent(self):
        # Test register Intent object
        s = TestSkill1()
        s.bind(self.emitter)
        s.initialize()
        expected = [{'at_least_one': [],
                     'name': 'TestSkill1:a',
                     'optional': [],
                     'requires': [('Keyword', 'Keyword')]}]
        self.check_register_intent(expected)

        # Test register IntentBuilder object
        s = TestSkill2()
        s.bind(self.emitter)
        s.initialize()
        expected = [{'at_least_one': [],
                     'name': 'TestSkill2:a',
                     'optional': [],
                     'requires': [('Keyword', 'Keyword')]}]

        self.check_register_intent(expected)

        # Test register IntentBuilder object
        with self.assertRaises(ValueError):
            s = TestSkill3()
            s.bind(self.emitter)
            s.initialize()

    def check_register_intent_file(self, result_list):
        for type in self.emitter.get_types():
            self.assertEquals(type, 'padatious:register_intent')
        self.assertEquals(sorted(self.emitter.get_results()),
                          sorted(result_list))
        self.emitter.reset()

    def test_register_intent_file(self):
        s = TestSkill4()
        s.bind(self.emitter)
        s.vocab_dir = join(dirname(__file__), 'intent_file')
        s.initialize()

        expected = [{
            'file_name': join(dirname(__file__), 'intent_file', 'test.intent'),
            'intent_name': s.name + ':test.intent'}]

        self.check_register_intent_file(expected)

    def check_register_decorators(self, result_list):
        self.assertEquals(sorted(self.emitter.get_results()),
                          sorted(result_list))
        self.emitter.reset()

    def test_register_decorators(self):
        """ Test decorated intents """
        path_orig = sys.path
        sys.path.append(abspath(dirname(__file__)))
        TestSkill5 = __import__('decorator_test_skill').TestSkill
        s = TestSkill5()
        s.vocab_dir = join(dirname(__file__), 'intent_file')
        s.bind(self.emitter)
        s.initialize()
        s._register_decorated()
        expected = [{'at_least_one': [],
                     'name': 'TestSkill:a',
                     'optional': [],
                     'requires': [('Keyword', 'Keyword')]},
                    {
                     'file_name': join(dirname(__file__), 'intent_file',
                                       'test.intent'),
                     'intent_name': s.name + ':test.intent'}]

        self.check_register_decorators(expected)


class TestSkill1(MycroftSkill):
    """ Test skill for normal intent builder syntax """
    def initialize(self):
        i = IntentBuilder('a').require('Keyword').build()
        self.register_intent(i, self.handler)

    def handler(self, message):
        pass

    def stop(self):
        pass


class TestSkill2(MycroftSkill):
    """ Test skill for intent builder without .build() """
    def initialize(self):
        i = IntentBuilder('a').require('Keyword')
        self.register_intent(i, self.handler)

    def handler(self, message):
        pass

    def stop(self):
        pass


class TestSkill3(MycroftSkill):
    """ Test skill for invalid Intent for register_intent """
    def initialize(self):
        self.register_intent('string', self.handler)

    def handler(self, message):
        pass

    def stop(self):
        pass


class TestSkill4(MycroftSkill):
    """ Test skill for padatious intent """
    def initialize(self):
        self.register_intent_file('test.intent', self.handler)

    def handler(self, message):
        pass

    def stop(self):
        pass
