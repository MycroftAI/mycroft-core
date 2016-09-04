import unittest

from os.path import join, dirname, abspath
from re import error

from mycroft.skills.core import load_regex_from_file, load_regex, \
    load_vocab_from_file, load_vocabulary
from mycroft.util.log import getLogger

__author__ = 'eward'
logger = getLogger(__name__)


class MockEmitter(object):
    def __init__(self):
        self.reset()

    def emit(self, message):
        self.types.append(message.type)
        self.results.append(message.metadata)

    def get_types(self):
        return self.types

    def get_results(self):
        return self.results

    def reset(self):
        self.types = []
        self.results = []


class MycroftSkillTest(unittest.TestCase):
    emitter = MockEmitter()
    regex_path = abspath(join(dirname(__file__), '../regex_test'))
    vocab_path = abspath(join(dirname(__file__), '../vocab_test'))

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
                              'wolfram_alpha'))

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
        self.check_vocab(join(dirname(__file__), 'wolfram_alpha'))

    def test_load_vocab_fail(self):
        try:
            self.check_regex(join(dirname(__file__),
                                  'vocab_test_fail'))
        except OSError as e:
            self.assertEquals(e.strerror, 'No such file or directory')
