import unittest
from os.path import join, dirname

from mycroft.skills.core import load_regex_from_file, load_regex
from mycroft.util.log import getLogger

__author__ = 'eward'
logger = getLogger(__name__)


class MockEmitter(object):
    def __init__(self):
        self.types = []
        self.results = []

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

    def check_load_from_file(self, path, emitter, regex_list):
        load_regex_from_file(path, emitter)
        self.check_emitter(emitter, regex_list)

    def check_load(self, path, emitter, regex_list):
        load_regex(path, emitter)
        self.check_emitter(emitter, regex_list)

    def check_emitter(self, emitter, regex_list):
        for type in emitter.get_types():
            self.assertEquals(type, 'register_vocab')
        if not regex_list:
            self.assertEquals(emitter.get_results(), regex_list)
        for value in regex_list:
            self.assertTrue(value in emitter.get_results())
        self.emitter.reset()

    def test_load_regex_from_file_single(self):
        self.check_load_from_file(join(dirname(__file__),
                                       'regex_test', 'single.rx'),
                                  self.emitter,
                                  ['(?P<SingleTest>.*)'])

    def test_load_regex_from_file_multiple(self):
        self.check_load_from_file(join(dirname(__file__),
                                       'regex_test', 'multiple.rx'),
                                  self.emitter,
                                  ['(?P<MultipleTest1>.*)',
                                   '(?P<MultipleTest2>.*)'])

    def test_load_regex_from_file_none(self):
        self.check_load_from_file(join(dirname(__file__),
                                       'regex_test', 'none.rx'),
                                  self.emitter,
                                  [])

    def test_load_regex_from_file_fail(self):
        try:
            self.check_load_from_file(join(dirname(__file__),
                                           'regex_test', 'does_not_exist.rx'),
                                      self.emitter,
                                      [])
        except IOError as e:
            self.assertEquals(e.strerror, 'No such file or directory')

    def test_load_regex_full(self):
        self.check_load(join(dirname(__file__), 'regex_test'),
                        self.emitter,
                        ['(?P<MultipleTest1>.*)',
                         '(?P<MultipleTest2>.*)',
                         '(?P<SingleTest>.*)'])

    def test_load_regex_empty(self):
        self.check_load(join(dirname(__file__),
                             'regex_test_none'),
                        self.emitter,
                        [])

    def test_load_regex_fail(self):
        try:
            self.check_load(join(dirname(__file__),
                                 'regex_test_fail'),
                            self.emitter,
                            [])
        except OSError as e:
            self.assertEquals(e.strerror, 'No such file or directory')
