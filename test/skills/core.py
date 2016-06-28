import unittest
from re import error
from os.path import join, dirname, abspath

from mycroft.skills.core import load_regex_from_file, load_regex
from mycroft.util.log import getLogger

__author__ = 'eward'
logger = getLogger(__name__)


class MockEmitter(object):
    def __init__(self):
        self.reset()

    def emit(self, message):
        self.types.append(message.message_type)
        self.results.append(message.metadata['regex'])

    def get_types(self):
        return self.types

    def get_results(self):
        return self.results

    def reset(self):
        self.types = []
        self.results = []


class MycroftSkillTest(unittest.TestCase):
    emitter = MockEmitter()
    path = abspath(join(dirname(__file__), '../regex_test'))

    def check_load_from_file(self, filename, regex_list=[]):
        load_regex_from_file(join(self.path, filename), self.emitter)
        self.check_emitter(self.emitter, regex_list)

    def check_load(self, path, regex_list=[]):
        load_regex(path, self.emitter)
        self.check_emitter(self.emitter, regex_list)

    def check_emitter(self, emitter, regex_list):
        for regex_type in emitter.get_types():
            self.assertEquals(regex_type, 'register_vocab')
        if not regex_list:
            self.assertEquals(emitter.get_results(), regex_list)
        for value in regex_list:
            self.assertTrue(value in emitter.get_results())
        self.emitter.reset()

    def test_load_regex_from_file_single(self):
        self.check_load_from_file('valid/single.rx',
                                  ['(?P<SingleTest>.*)'])

    def test_load_regex_from_file_multiple(self):
        self.check_load_from_file('valid/multiple.rx',
                                  ['(?P<MultipleTest1>.*)',
                                   '(?P<MultipleTest2>.*)'])

    def test_load_regex_from_file_none(self):
        self.check_load_from_file('invalid/none.rx')

    def test_load_regex_from_file_invalid(self):
        try:
            self.check_load_from_file('invalid/invalid.rx')
        except error as e:
            self.assertEquals(e.__str__(),
                              'unexpected end of regular expression')

    def test_load_regex_from_file_does_not_exist(self):
        try:
            self.check_load_from_file('does_not_exist.rx')
        except IOError as e:
            self.assertEquals(e.strerror, 'No such file or directory')

    def test_load_regex_full(self):
        self.check_load(join(self.path, 'valid'),
                        ['(?P<MultipleTest1>.*)',
                         '(?P<MultipleTest2>.*)',
                         '(?P<SingleTest>.*)'])

    def test_load_regex_empty(self):
        self.check_load(join(dirname(__file__),
                             'wolfram_alpha'))

    def test_load_regex_fail(self):
        try:
            self.check_load(join(dirname(__file__),
                                 'regex_test_fail'))
        except OSError as e:
            self.assertEquals(e.strerror, 'No such file or directory')
