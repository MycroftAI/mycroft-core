# -*- coding: utf-8 -*-
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
import sys
import unittest

import mock
from adapt.intent import IntentBuilder
from os.path import join, dirname, abspath
from re import error
from datetime import datetime

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.skills.skill_data import load_regex_from_file, load_regex, \
    load_vocab_from_file, load_vocabulary
from mycroft.skills.core import MycroftSkill, load_skill, \
    create_skill_descriptor, open_intent_envelope


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

    def check_vocab_from_file(self, filename, vocab_type=None,
                              result_list=None):
        result_list = result_list or []
        load_vocab_from_file(join(self.vocab_path, filename), vocab_type,
                             self.emitter)
        self.check_emitter(result_list)

    def check_regex_from_file(self, filename, result_list=None):
        result_list = result_list or []
        load_regex_from_file(join(self.regex_path, filename), self.emitter, 0)
        self.check_emitter(result_list)

    def check_vocab(self, path, result_list=None):
        result_list = result_list or []
        load_vocabulary(path, self.emitter, 0)
        self.check_emitter(result_list)

    def check_regex(self, path, result_list=None):
        result_list = result_list or []
        load_regex(path, self.emitter, 0)
        self.check_emitter(result_list)

    def check_emitter(self, result_list):
        for type in self.emitter.get_types():
            self.assertEquals(type, 'register_vocab')
        self.assertEquals(sorted(self.emitter.get_results()),
                          sorted(result_list))
        self.emitter.reset()

    def test_load_regex_from_file_single(self):
        self.check_regex_from_file('valid/single.rx',
                                   [{'regex': '(?P<ASingleTest>.*)'}])

    def test_load_regex_from_file_multiple(self):
        self.check_regex_from_file('valid/multiple.rx',
                                   [{'regex': '(?P<AMultipleTest1>.*)'},
                                    {'regex': '(?P<AMultipleTest2>.*)'}])

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
                         [{'regex': '(?P<AMultipleTest1>.*)'},
                          {'regex': '(?P<AMultipleTest2>.*)'},
                          {'regex': '(?P<ASingleTest>.*)'}])

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
                         [{'start': 'test', 'end': 'Asingle'},
                          {'start': 'water', 'end': 'Asinglealias'},
                          {'start': 'watering', 'end': 'Asinglealias',
                           'alias_of': 'water'},
                          {'start': 'animal', 'end': 'Amultiple'},
                          {'start': 'animals', 'end': 'Amultiple'},
                          {'start': 'chair', 'end': 'Amultiplealias'},
                          {'start': 'chairs', 'end': 'Amultiplealias',
                           'alias_of': 'chair'},
                          {'start': 'table', 'end': 'Amultiplealias'},
                          {'start': 'tables', 'end': 'Amultiplealias',
                           'alias_of': 'table'}])

    def test_load_vocab_empty(self):
        self.check_vocab(join(dirname(__file__), 'empty_dir'))

    def test_load_vocab_fail(self):
        try:
            self.check_regex(join(dirname(__file__),
                                  'vocab_test_fail'))
        except OSError as e:
            self.assertEquals(e.strerror, 'No such file or directory')

    def test_open_envelope(self):
        name = 'Jerome'
        intent = IntentBuilder(name).require('Keyword')
        intent.name = name
        m = Message("register_intent", intent.__dict__)
        unpacked_intent = open_intent_envelope(m)
        self.assertEqual(intent.__dict__, unpacked_intent.__dict__)

    def test_load_skill(self):
        """ Verify skill load function. """
        e_path = join(dirname(__file__), 'test_skill')
        s = load_skill(create_skill_descriptor(e_path), MockEmitter(), 847)
        self.assertEquals(s._dir, e_path)
        self.assertEquals(s.skill_id, 847)
        self.assertEquals(s.name, 'LoadTestSkill')

    def check_detach_intent(self):
        self.assertTrue(len(self.emitter.get_types()) > 0)
        for msg_type in self.emitter.get_types():
            self.assertEquals(msg_type, 'detach_intent')
        self.emitter.reset()

    def check_register_intent(self, result_list):
        for type in self.emitter.get_types():
            self.assertEquals(type, 'register_intent')
        self.assertEquals(sorted(self.emitter.get_results()),
                          sorted(result_list))
        self.emitter.reset()

    def check_register_vocabulary(self, result_list):
        for type in self.emitter.get_types():
            self.assertEquals(type, 'register_vocab')
        self.assertEquals(sorted(self.emitter.get_results()),
                          sorted(result_list))
        self.emitter.reset()

    def test_register_intent(self):
        # Test register Intent object
        s = TestSkill1()
        s.bind(self.emitter)
        s.initialize()
        expected = [{'at_least_one': [],
                     'name': '0:a',
                     'optional': [],
                     'requires': [('AKeyword', 'AKeyword')]}]
        self.check_register_intent(expected)

        # Test register IntentBuilder object
        s = TestSkill2()
        s.bind(self.emitter)
        s.initialize()
        expected = [{'at_least_one': [],
                     'name': '0:a',
                     'optional': [],
                     'requires': [('AKeyword', 'AKeyword')]}]

        self.check_register_intent(expected)

        # Test register IntentBuilder object
        with self.assertRaises(ValueError):
            s = TestSkill3()
            s.bind(self.emitter)
            s.initialize()

    def test_enable_disable_intent(self):
        """Test disable/enable intent."""
        # Setup basic test
        s = TestSkill1()
        s.bind(self.emitter)
        s.initialize()
        expected = [{'at_least_one': [],
                     'name': '0:a',
                     'optional': [],
                     'requires': [('AKeyword', 'AKeyword')]}]
        self.check_register_intent(expected)

        # Test disable/enable cycle
        s.disable_intent('a')
        self.check_detach_intent()
        s.enable_intent('a')
        self.check_register_intent(expected)

    def test_register_vocab(self):
        """Test disable/enable intent."""
        # Setup basic test
        s = TestSkill1()
        s.bind(self.emitter)
        s.initialize()

        # Normal vocaubulary
        self.emitter.reset()
        expected = [{'start': 'hello', 'end': 'AHelloKeyword'}]
        s.register_vocabulary('hello', 'HelloKeyword')
        self.check_register_vocabulary(expected)
        # Regex
        s.register_regex('weird (?P<Weird>.+) stuff')
        expected = [{'regex': 'weird (?P<AWeird>.+) stuff'}]
        self.check_register_vocabulary(expected)

    def check_register_object_file(self, types_list, result_list):
        self.assertEquals(sorted(self.emitter.get_types()),
                          sorted(types_list))
        self.assertEquals(sorted(self.emitter.get_results()),
                          sorted(result_list))
        self.emitter.reset()

    def test_register_intent_file(self):
        s = TestSkill4()
        s.bind(self.emitter)
        s.vocab_dir = join(dirname(__file__), 'intent_file')
        s.initialize()

        expected_types = [
            'padatious:register_intent',
            'padatious:register_entity'
        ]

        expected_results = [
            {
                'file_name': join(dirname(__file__),
                                  'intent_file', 'test.intent'),
                'name': str(s.skill_id) + ':test.intent'
            },
            {
                'file_name': join(dirname(__file__),
                                  'intent_file', 'test_ent.entity'),
                'name': str(s.skill_id) + ':test_ent'
            }
        ]

        self.check_register_object_file(expected_types, expected_results)

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
                     'name': '0:a',
                     'optional': [],
                     'requires': [('AKeyword', 'AKeyword')]},
                    {
                     'file_name': join(dirname(__file__), 'intent_file',
                                       'test.intent'),
                     'name': str(s.skill_id) + ':test.intent'}]

        self.check_register_decorators(expected)

    def test_failing_set_context(self):
        s = TestSkill1()
        s.bind(self.emitter)
        with self.assertRaises(ValueError):
            s.set_context(1)
        with self.assertRaises(ValueError):
            s.set_context(1, 1)
        with self.assertRaises(ValueError):
            s.set_context('Kowabunga', 1)

    def test_set_context(self):
        def check_set_context(result_list):
            for type in self.emitter.get_types():
                self.assertEquals(type, 'add_context')
            self.assertEquals(sorted(self.emitter.get_results()),
                              sorted(result_list))
            self.emitter.reset()

        s = TestSkill1()
        s.bind(self.emitter)
        # No context content
        s.set_context('TurtlePower')
        expected = [{'context': 'ATurtlePower', 'word': ''}]
        check_set_context(expected)

        # context with content
        s.set_context('Technodrome', 'Shredder')
        expected = [{'context': 'ATechnodrome', 'word': 'Shredder'}]
        check_set_context(expected)

        # UTF-8 context
        s.set_context(u'Smörgåsbord€15')
        expected = [{'context': u'ASmörgåsbord€15', 'word': ''}]
        check_set_context(expected)

        self.emitter.reset()

    def test_failing_remove_context(self):
        s = TestSkill1()
        s.bind(self.emitter)
        with self.assertRaises(ValueError):
            s.remove_context(1)

    def test_remove_context(self):
        def check_remove_context(result_list):
            for type in self.emitter.get_types():
                self.assertEquals(type, 'remove_context')
            self.assertEquals(sorted(self.emitter.get_results()),
                              sorted(result_list))
            self.emitter.reset()

        s = TestSkill1()
        s.bind(self.emitter)
        s.remove_context('Donatello')
        expected = [{'context': 'Donatello'}]
        check_remove_context(expected)

    @mock.patch.object(Configuration, 'get')
    def test_skill_location(self, mock_config_get):
        test_config = {
            "location": {
                "city": {
                    "code": "Lawrence",
                    "name": "Lawrence",
                    "state": {
                        "code": "KS",
                        "name": "Kansas",
                        "country": {
                            "code": "US",
                            "name": "United States"
                        }
                    }
                },
                "coordinate": {
                    "latitude": 38.971669,
                    "longitude": -95.23525
                },
                "timezone": {
                    "code": "America/Chicago",
                    "name": "Central Standard Time",
                    "dstOffset": 3600000,
                    "offset": -21600000
                }
            }
        }
        mock_config_get.return_value = test_config
        s = TestSkill1()
        self.assertEqual(s.location, test_config.get('location'))
        self.assertEqula(s.location_pretty,
                         test_config['location']['city']['name'])
        self.assertEqual(s.location_timezone,
                         test_config['location']['timezone']['code'])

    @mock.patch.object(Configuration, 'get')
    def test_skill_location(self, mock_config_get):
        test_config = {}
        mock_config_get.return_value = test_config
        s = TestSkill1()
        self.assertEqual(s.location, None)
        self.assertEqual(s.location_pretty, None)
        self.assertEqual(s.location_timezone, None)

    @mock.patch.object(Configuration, 'get')
    def test_add_event(self, mock_config_get):
        test_config = {
            'skills': {
            }
        }
        mock_config_get.return_value = test_config
        emitter = mock.MagicMock()
        s = TestSkill1()
        s.bind(emitter)
        s.add_event('handler1', s.handler)
        # Check that the handler was registered with the emitter
        self.assertEqual(emitter.on.call_args[0][0], 'handler1')
        # Check that the handler was stored in the skill
        self.assertTrue('handler1' in zip(*s.events)[0])

    @mock.patch.object(Configuration, 'get')
    def test_remove_event(self, mock_config_get):
        test_config = {
            'skills': {
            }
        }
        mock_config_get.return_value = test_config
        emitter = mock.MagicMock()
        s = TestSkill1()
        s.bind(emitter)
        s.add_event('handler1', s.handler)
        self.assertTrue('handler1' in zip(*s.events)[0])
        # Remove event handler
        s.remove_event('handler1')
        # make sure it's not in the event list anymore
        self.assertTrue('handler1' not in zip(*s.events)[0])
        # Check that the handler was registered with the emitter
        self.assertEqual(emitter.remove.call_args[0][0], 'handler1')

    @mock.patch.object(Configuration, 'get')
    def test_add_scheduled_event(self, mock_config_get):
        test_config = {
            'skills': {
            }
        }
        mock_config_get.return_value = test_config
        emitter = mock.MagicMock()
        s = TestSkill1()
        s.bind(emitter)
        s.schedule_event(s.handler, datetime.now(), name='sched_handler1')
        # Check that the handler was registered with the emitter
        self.assertEqual(emitter.once.call_args[0][0], '0:sched_handler1')
        self.assertTrue('0:sched_handler1' in zip(*s.events)[0])

    @mock.patch.object(Configuration, 'get')
    def test_remove_scheduled_event(self, mock_config_get):
        test_config = {
            'skills': {
            }
        }
        mock_config_get.return_value = test_config
        emitter = mock.MagicMock()
        s = TestSkill1()
        s.bind(emitter)
        s.schedule_event(s.handler, datetime.now(), name='sched_handler1')
        # Check that the handler was registered with the emitter
        self.assertTrue('0:sched_handler1' in zip(*s.events)[0])
        s.cancel_scheduled_event('sched_handler1')
        # Check that the handler was removed
        self.assertEqual(emitter.remove.call_args[0][0], '0:sched_handler1')
        self.assertTrue('0:sched_handler1' not in zip(*s.events)[0])

    @mock.patch.object(Configuration, 'get')
    def test_run_scheduled_event(self, mock_config_get):
        test_config = {
            'skills': {
            }
        }
        mock_config_get.return_value = test_config
        emitter = mock.MagicMock()
        s = TestSkill1()
        with mock.patch.object(s, '_settings',
                               create=True, value=mock.MagicMock()):
            s.bind(emitter)
            s.schedule_event(s.handler, datetime.now(), name='sched_handler1')
            # Check that the handler was registered with the emitter
            emitter.once.call_args[0][1](Message('message'))
            # Check that the handler was run
            self.assertTrue(s.handler_run)
            # Check that the handler was removed from the list of registred
            # handler
            self.assertTrue('0:sched_handler1' not in zip(*s.events)[0])


class TestSkill1(MycroftSkill):
    def __init__(self):
        super(TestSkill1, self).__init__()
        self.handler_run = False

    """ Test skill for normal intent builder syntax """
    def initialize(self):
        i = IntentBuilder('a').require('Keyword').build()
        self.register_intent(i, self.handler)

    def handler(self, message):
        self.handler_run = True

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
        self.register_entity_file('test_ent.entity')

    def handler(self, message):
        pass

    def stop(self):
        pass
