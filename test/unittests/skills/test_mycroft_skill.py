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

from unittest.mock import MagicMock, patch
from adapt.intent import IntentBuilder
from os.path import join, dirname, abspath
from re import error
from datetime import datetime
import json

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.skills.skill_data import (load_regex_from_file, load_regex,
                                       load_vocabulary, read_vocab_file)
from mycroft.skills.core import MycroftSkill, resting_screen_handler
from mycroft.skills.intent_service import open_intent_envelope

from test.util import base_config

BASE_CONF = base_config()


class MockEmitter(object):
    def __init__(self):
        self.reset()

    def emit(self, message):
        self.types.append(message.msg_type)
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


def vocab_base_path():
    return join(dirname(__file__), '..', 'vocab_test')


class TestFunction(unittest.TestCase):
    def test_resting_screen_handler(self):
        class T(MycroftSkill):
            def __init__(self):
                self.name = 'TestObject'

            @resting_screen_handler('humbug')
            def f(self):
                pass

        test_class = T()
        self.assertTrue('resting_handler' in dir(test_class.f))
        self.assertEquals(test_class.f.resting_handler, 'humbug')


class TestMycroftSkill(unittest.TestCase):
    emitter = MockEmitter()
    regex_path = abspath(join(dirname(__file__), '../regex_test'))
    vocab_path = abspath(join(dirname(__file__), '../vocab_test'))

    def setUp(self):
        self.emitter.reset()
        self.local_settings_mock = self._mock_local_settings()

    def _mock_local_settings(self):
        local_settings_patch = patch(
            'mycroft.skills.mycroft_skill.mycroft_skill.get_local_settings'
        )
        self.addCleanup(local_settings_patch.stop)
        local_settings_mock = local_settings_patch.start()
        local_settings_mock.return_value = True

        return local_settings_mock

    def check_vocab(self, filename, results=None):
        results = results or {}
        intents = load_vocabulary(join(self.vocab_path, filename), 'A')
        self.compare_dicts(intents, results)

    def check_regex_from_file(self, filename, result_list=None):
        result_list = result_list or []
        regex_file = join(self.regex_path, filename)
        self.assertEqual(sorted(load_regex_from_file(regex_file, 'A')),
                         sorted(result_list))

    def compare_dicts(self, d1, d2):
        self.assertEqual(json.dumps(d1, sort_keys=True),
                         json.dumps(d2, sort_keys=True))

    def check_read_vocab_file(self, path, result_list=None):
        resultlist = result_list or []
        self.assertEqual(sorted(read_vocab_file(path)), sorted(result_list))

    def check_regex(self, path, result_list=None):
        result_list = result_list or []
        self.assertEqual(sorted(load_regex(path, 'A')), sorted(result_list))

    def check_emitter(self, result_list):
        for msg_type in self.emitter.get_types():
            self.assertEqual(msg_type, 'register_vocab')
        self.assertEqual(sorted(self.emitter.get_results(),
                                key=lambda d: sorted(d.items())),
                         sorted(result_list, key=lambda d: sorted(d.items())))
        self.emitter.reset()

    def test_load_regex_from_file_single(self):
        self.check_regex_from_file('valid/single.rx',
                                   ['(?P<ASingleTest>.*)'])

    def test_load_regex_from_file_multiple(self):
        self.check_regex_from_file('valid/multiple.rx',
                                   ['(?P<AMultipleTest1>.*)',
                                    '(?P<AMultipleTest2>.*)'])

    def test_load_regex_from_file_none(self):
        self.check_regex_from_file('invalid/none.rx')

    def test_load_regex_from_file_invalid(self):
        with self.assertRaises(error):
            self.check_regex_from_file('invalid/invalid.rx')

    def test_load_regex_from_file_does_not_exist(self):
        with self.assertRaises(IOError):
            self.check_regex_from_file('does_not_exist.rx')

    def test_load_regex_full(self):
        self.check_regex(join(self.regex_path, 'valid'),
                         ['(?P<AMultipleTest1>.*)',
                          '(?P<AMultipleTest2>.*)',
                          '(?P<ASingleTest>.*)'])

    def test_load_regex_empty(self):
        self.check_regex(join(dirname(__file__), 'empty_dir'))

    def test_load_regex_fail(self):
        try:
            self.check_regex(join(dirname(__file__), 'regex_test_fail'))
        except OSError as e:
            self.assertEqual(e.strerror, 'No such file or directory')

    def test_load_vocab_file_single(self):
        self.check_read_vocab_file(join(vocab_base_path(), 'valid/single.voc'),
                                   [['test']])

    def test_load_vocab_from_file_single_alias(self):
        self.check_read_vocab_file(join(vocab_base_path(),
                                        'valid/singlealias.voc'),
                                   [['water', 'watering']])

    def test_load_vocab_from_file_multiple_alias(self):
        self.check_read_vocab_file(join(vocab_base_path(),
                                        'valid/multiplealias.voc'),
                                   [['chair', 'chairs'], ['table', 'tables']])

    def test_load_vocab_from_file_does_not_exist(self):
        try:
            self.check_read_vocab_file('does_not_exist.voc')
        except IOError as e:
            self.assertEqual(e.strerror, 'No such file or directory')

    def test_load_vocab_full(self):
        self.check_vocab(join(self.vocab_path, 'valid'),
                         {
                             'Asingle': [['test']],
                             'Asinglealias': [['water', 'watering']],
                             'Amultiple': [['animal'], ['animals']],
                             'Amultiplealias': [['chair', 'chairs'],
                                                ['table', 'tables']]
                        })

    def test_load_vocab_empty(self):
        self.check_vocab(join(dirname(__file__), 'empty_dir'))

    def test_load_vocab_fail(self):
        try:
            self.check_regex(join(dirname(__file__),
                                  'vocab_test_fail'))
        except OSError as e:
            self.assertEqual(e.strerror, 'No such file or directory')

    def test_open_envelope(self):
        name = 'Jerome'
        intent = IntentBuilder(name).require('Keyword')
        intent.name = name
        m = Message("register_intent", intent.__dict__)
        unpacked_intent = open_intent_envelope(m)
        self.assertEqual(intent.__dict__, unpacked_intent.__dict__)

    def check_detach_intent(self):
        self.assertTrue(len(self.emitter.get_types()) > 0)
        for msg_type in self.emitter.get_types():
            self.assertEqual(msg_type, 'detach_intent')
        self.emitter.reset()

    def check_register_intent(self, result_list):
        for msg_type in self.emitter.get_types():
            self.assertEqual(msg_type, 'register_intent')
        self.assertEqual(sorted(self.emitter.get_results()),
                         sorted(result_list))
        self.emitter.reset()

    def check_register_vocabulary(self, result_list):
        for msg_type in self.emitter.get_types():
            self.assertEqual(msg_type, 'register_vocab')
        self.assertEqual(sorted(self.emitter.get_results()),
                         sorted(result_list))
        self.emitter.reset()

    def test_register_intent(self):
        # Test register Intent object
        s = SimpleSkill1()
        s.bind(self.emitter)
        s.initialize()
        expected = [{'at_least_one': [],
                     'name': 'A:a',
                     'optional': [],
                     'requires': [('AKeyword', 'AKeyword')]}]
        self.check_register_intent(expected)

        # Test register IntentBuilder object
        s = SimpleSkill2()
        s.bind(self.emitter)
        s.initialize()
        expected = [{'at_least_one': [],
                     'name': 'A:a',
                     'optional': [],
                     'requires': [('AKeyword', 'AKeyword')]}]

        self.check_register_intent(expected)

        # Test register IntentBuilder object
        with self.assertRaises(ValueError):
            s = SimpleSkill3()
            s.bind(self.emitter)
            s.initialize()

    def test_enable_disable_intent(self):
        """Test disable/enable intent."""
        # Setup basic test
        s = SimpleSkill1()
        s.bind(self.emitter)
        s.initialize()
        expected = [{'at_least_one': [],
                     'name': 'A:a',
                     'optional': [],
                     'requires': [('AKeyword', 'AKeyword')]}]
        self.check_register_intent(expected)

        # Test disable/enable cycle
        s.disable_intent('a')
        self.check_detach_intent()
        s.enable_intent('a')
        self.check_register_intent(expected)

    def test_enable_disable_intent_handlers(self):
        """Test disable/enable intent."""
        # Setup basic test
        s = SimpleSkill1()
        s.bind(self.emitter)
        s.initialize()
        expected = [{'at_least_one': [],
                     'name': 'A:a',
                     'optional': [],
                     'requires': [('AKeyword', 'AKeyword')]}]
        self.check_register_intent(expected)

        # Test disable/enable cycle
        msg = Message('test.msg', data={'intent_name': 'a'})
        s.handle_disable_intent(msg)
        self.check_detach_intent()
        s.handle_enable_intent(msg)
        self.check_register_intent(expected)

    def test_register_vocab(self):
        """Test disable/enable intent."""
        # Setup basic test
        s = SimpleSkill1()
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
        self.assertEqual(sorted(self.emitter.get_types()),
                         sorted(types_list))
        self.assertEqual(sorted(self.emitter.get_results(),
                                key=lambda d: sorted(d.items())),
                         sorted(result_list, key=lambda d: sorted(d.items())))
        self.emitter.reset()

    def test_register_intent_file(self):
        self._test_intent_file(SimpleSkill4())

    def test_register_intent_intent_file(self):
        """Test register intent files using register_intent."""
        self._test_intent_file(SimpleSkill6())

    def _test_intent_file(self, s):
        s.root_dir = abspath(join(dirname(__file__), 'intent_file'))
        s.bind(self.emitter)
        s.initialize()

        expected_types = [
            'padatious:register_intent',
            'padatious:register_entity'
        ]

        expected_results = [
            {
                'file_name': join(dirname(__file__), 'intent_file',
                                  'vocab', 'en-us', 'test.intent'),
                'name': str(s.skill_id) + ':test.intent'
            },
            {
                'file_name': join(dirname(__file__), 'intent_file',
                                  'vocab', 'en-us', 'test_ent.entity'),
                'name': str(s.skill_id) + ':test_ent'
            }
        ]
        self.check_register_object_file(expected_types, expected_results)

    def check_register_decorators(self, result_list):
        self.assertEqual(sorted(self.emitter.get_results(),
                                key=lambda d: sorted(d.items())),
                         sorted(result_list, key=lambda d: sorted(d.items())))
        self.emitter.reset()

    def test_register_decorators(self):
        """ Test decorated intents """
        path_orig = sys.path
        sys.path.append(abspath(dirname(__file__)))
        SimpleSkill5 = __import__('decorator_test_skill').TestSkill
        s = SimpleSkill5()
        s.skill_id = 'A'
        s.bind(self.emitter)
        s.root_dir = abspath(join(dirname(__file__), 'intent_file'))
        s.initialize()
        s._register_decorated()
        expected = [{'at_least_one': [],
                     'name': 'A:a',
                     'optional': [],
                     'requires': [('AKeyword', 'AKeyword')]},
                    {
                     'file_name': join(dirname(__file__), 'intent_file',
                                       'vocab', 'en-us', 'test.intent'),
                     'name': str(s.skill_id) + ':test.intent'}]

        self.check_register_decorators(expected)
        # Restore sys.path
        sys.path = path_orig

    def test_failing_set_context(self):
        s = SimpleSkill1()
        s.bind(self.emitter)
        with self.assertRaises(ValueError):
            s.set_context(1)
        with self.assertRaises(ValueError):
            s.set_context(1, 1)
        with self.assertRaises(ValueError):
            s.set_context('Kowabunga', 1)

    def test_set_context(self):
        def check_set_context(result_list):
            for msg_type in self.emitter.get_types():
                self.assertEqual(msg_type, 'add_context')
            self.assertEqual(sorted(self.emitter.get_results()),
                             sorted(result_list))
            self.emitter.reset()

        s = SimpleSkill1()
        s.bind(self.emitter)
        # No context content
        s.set_context('TurtlePower')
        expected = [{'context': 'ATurtlePower', 'origin': '', 'word': ''}]
        check_set_context(expected)

        # context with content
        s.set_context('Technodrome', 'Shredder')
        expected = [{'context': 'ATechnodrome', 'origin': '',
                     'word': 'Shredder'}]
        check_set_context(expected)

        # UTF-8 context
        s.set_context(u'Smörgåsbord€15')
        expected = [{'context': u'ASmörgåsbord€15', 'origin': '', 'word': ''}]
        check_set_context(expected)

        self.emitter.reset()

    def test_failing_remove_context(self):
        s = SimpleSkill1()
        s.bind(self.emitter)
        with self.assertRaises(ValueError):
            s.remove_context(1)

    def test_remove_context(self):
        def check_remove_context(result_list):
            for type in self.emitter.get_types():
                self.assertEqual(type, 'remove_context')
            self.assertEqual(sorted(self.emitter.get_results()),
                             sorted(result_list))
            self.emitter.reset()

        s = SimpleSkill1()
        s.bind(self.emitter)
        s.remove_context('Donatello')
        expected = [{'context': 'ADonatello'}]
        check_remove_context(expected)

    @patch.dict(Configuration._Configuration__config, BASE_CONF)
    def test_skill_location(self):
        s = SimpleSkill1()
        self.assertEqual(s.location, BASE_CONF.get('location'))
        self.assertEqual(s.location_pretty,
                         BASE_CONF['location']['city']['name'])
        self.assertEqual(s.location_timezone,
                         BASE_CONF['location']['timezone']['code'])

    @patch.dict(Configuration._Configuration__config, BASE_CONF)
    def test_add_event(self):
        emitter = MagicMock()
        s = SimpleSkill1()
        s.bind(emitter)
        s.add_event('handler1', s.handler)
        # Check that the handler was registered with the emitter
        self.assertEqual(emitter.on.call_args[0][0], 'handler1')
        # Check that the handler was stored in the skill
        self.assertTrue('handler1' in [e[0] for e in s.events])

    @patch.dict(Configuration._Configuration__config, BASE_CONF)
    def test_remove_event(self):
        emitter = MagicMock()
        s = SimpleSkill1()
        s.bind(emitter)
        s.add_event('handler1', s.handler)
        self.assertTrue('handler1' in [e[0] for e in s.events])
        # Remove event handler
        s.remove_event('handler1')
        # make sure it's not in the event list anymore
        self.assertTrue('handler1' not in [e[0] for e in s.events])
        # Check that the handler was registered with the emitter
        self.assertEqual(emitter.remove_all_listeners.call_args[0][0],
                         'handler1')

    @patch.dict(Configuration._Configuration__config, BASE_CONF)
    def test_add_scheduled_event(self):
        emitter = MagicMock()
        s = SimpleSkill1()
        s.bind(emitter)

        s.schedule_event(s.handler, datetime.now(), name='datetime_handler')
        # Check that the handler was registered with the emitter
        self.assertEqual(emitter.once.call_args[0][0], 'A:datetime_handler')
        sched_events = [e[0] for e in s.event_scheduler.events]
        self.assertTrue('A:datetime_handler' in sched_events)

        s.schedule_event(s.handler, 1, name='int_handler')
        # Check that the handler was registered with the emitter
        self.assertEqual(emitter.once.call_args[0][0], 'A:int_handler')
        sched_events = [e[0] for e in s.event_scheduler.events]
        self.assertTrue('A:int_handler' in sched_events)

        s.schedule_event(s.handler, .5, name='float_handler')
        # Check that the handler was registered with the emitter
        self.assertEqual(emitter.once.call_args[0][0], 'A:float_handler')
        sched_events = [e[0] for e in s.event_scheduler.events]
        self.assertTrue('A:float_handler' in sched_events)

    @patch.dict(Configuration._Configuration__config, BASE_CONF)
    def test_remove_scheduled_event(self):
        emitter = MagicMock()
        s = SimpleSkill1()
        s.bind(emitter)
        s.schedule_event(s.handler, datetime.now(), name='sched_handler1')
        # Check that the handler was registered with the emitter
        events = [e[0] for e in s.event_scheduler.events]
        print(events)
        self.assertTrue('A:sched_handler1' in events)
        s.cancel_scheduled_event('sched_handler1')
        # Check that the handler was removed
        self.assertEqual(emitter.remove_all_listeners.call_args[0][0],
                         'A:sched_handler1')
        events = [e[0] for e in s.event_scheduler.events]
        self.assertTrue('A:sched_handler1' not in events)

    @patch.dict(Configuration._Configuration__config, BASE_CONF)
    def test_run_scheduled_event(self):
        emitter = MagicMock()
        s = SimpleSkill1()
        with patch.object(s, '_settings',
                          create=True, value=MagicMock()):
            s.bind(emitter)
            s.schedule_event(s.handler, datetime.now(), name='sched_handler1')
            # Check that the handler was registered with the emitter
            emitter.once.call_args[0][1](Message('message'))
            # Check that the handler was run
            self.assertTrue(s.handler_run)
            # Check that the handler was removed from the list of registred
            # handler
            self.assertTrue('A:sched_handler1' not in [e[0] for e in s.events])

    def test_voc_match(self):
        s = SimpleSkill1()
        s.root_dir = abspath(dirname(__file__))

        self.assertTrue(s.voc_match("turn off the lights", "turn_off_test"))
        self.assertTrue(s.voc_match("would you please turn off the lights",
                                    "turn_off_test"))
        self.assertFalse(s.voc_match("return office", "turn_off_test"))
        self.assertTrue(s.voc_match("switch off the lights", "turn_off_test"))
        self.assertFalse(s.voc_match("", "turn_off_test"))
        self.assertFalse(s.voc_match("switch", "turn_off_test"))
        self.assertFalse(s.voc_match("My hovercraft is full of eels",
                                     "turn_off_test"))

        self.assertTrue(s.voc_match("turn off the lights", "turn_off2_test"))
        self.assertFalse(s.voc_match("return office", "turn_off2_test"))
        self.assertTrue(s.voc_match("switch off the lights", "turn_off2_test"))
        self.assertFalse(s.voc_match("", "turn_off_test"))
        self.assertFalse(s.voc_match("switch", "turn_off_test"))
        self.assertFalse(s.voc_match("My hovercraft is full of eels",
                                     "turn_off_test"))


class _TestSkill(MycroftSkill):
    def __init__(self):
        super().__init__()
        self.skill_id = 'A'


class SimpleSkill1(_TestSkill):
    def __init__(self):
        super(SimpleSkill1, self).__init__()
        self.handler_run = False

    """ Test skill for normal intent builder syntax """
    def initialize(self):
        i = IntentBuilder('a').require('Keyword').build()
        self.register_intent(i, self.handler)

    def handler(self, message):
        self.handler_run = True

    def stop(self):
        pass


class SimpleSkill2(_TestSkill):
    """ Test skill for intent builder without .build() """
    skill_id = 'A'

    def initialize(self):
        i = IntentBuilder('a').require('Keyword')
        self.register_intent(i, self.handler)

    def handler(self, message):
        pass

    def stop(self):
        pass


class SimpleSkill3(_TestSkill):
    """ Test skill for invalid Intent for register_intent """
    skill_id = 'A'

    def initialize(self):
        self.register_intent('string', self.handler)

    def handler(self, message):
        pass

    def stop(self):
        pass


class SimpleSkill4(_TestSkill):
    """ Test skill for padatious intent """
    skill_id = 'A'

    def initialize(self):
        self.register_intent_file('test.intent', self.handler)
        self.register_entity_file('test_ent.entity')

    def handler(self, message):
        pass

    def stop(self):
        pass


class SimpleSkill6(_TestSkill):
    """ Test skill for padatious intent """
    skill_id = 'A'

    def initialize(self):
        self.register_intent('test.intent', self.handler)
        self.register_entity_file('test_ent.entity')

    def handler(self, message):
        pass
