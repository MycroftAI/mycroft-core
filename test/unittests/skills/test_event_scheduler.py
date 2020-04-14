"""
    Test cases regarding the event scheduler.
"""

import unittest
import time

from unittest.mock import MagicMock, patch
from mycroft.messagebus.client.threaded_event_emitter import (
        ThreadedEventEmitter)
from mycroft.skills.event_scheduler import (EventScheduler,
                                            EventSchedulerInterface)


class TestEventScheduler(unittest.TestCase):
    @patch('threading.Thread')
    @patch('json.load')
    @patch('json.dump')
    @patch('builtins.open')
    def test_create(self, mock_open, mock_json_dump, mock_load, mock_thread):
        """
            Test creating and shutting down event_scheduler.
        """
        mock_load.return_value = ''
        mock_open.return_value = MagicMock()
        emitter = MagicMock()
        es = EventScheduler(emitter)
        es.shutdown()
        self.assertEqual(mock_json_dump.call_args[0][0], {})

    @patch('threading.Thread')
    @patch('json.load')
    @patch('json.dump')
    @patch('builtins.open')
    def test_add_remove(self, mock_open, mock_json_dump,
                        mock_load, mock_thread):
        """
            Test add an event and then remove it.
        """
        # Thread start is mocked so will not actually run the thread loop
        mock_load.return_value = ''
        mock_open.return_value = MagicMock()
        emitter = MagicMock()
        es = EventScheduler(emitter)

        # 900000000000 should be in the future for a long time
        es.schedule_event('test', 90000000000, None)
        es.schedule_event('test-2', 90000000000, None)

        es.check_state()  # run one cycle
        self.assertTrue('test' in es.events)
        self.assertTrue('test-2' in es.events)

        es.remove_event('test')
        es.check_state()  # run one cycle
        self.assertTrue('test' not in es.events)
        self.assertTrue('test-2' in es.events)
        es.shutdown()

    @patch('threading.Thread')
    @patch('json.load')
    @patch('json.dump')
    @patch('builtins.open')
    def test_save(self, mock_open, mock_dump, mock_load, mock_thread):
        """
            Test save functionality.
        """
        mock_load.return_value = ''
        mock_open.return_value = MagicMock()
        emitter = MagicMock()
        es = EventScheduler(emitter)

        # 900000000000 should be in the future for a long time
        es.schedule_event('test', 900000000000, None)
        es.schedule_event('test-repeat', 910000000000, 60)
        es.check_state()

        es.shutdown()

        # Make sure the dump method wasn't called with test-repeat
        self.assertEqual(mock_dump.call_args[0][0],
                         {'test': [(900000000000, None, {}, None)]})

    @patch('threading.Thread')
    @patch('json.load')
    @patch('json.dump')
    @patch('builtins.open')
    def test_send_event(self, mock_open, mock_dump, mock_load, mock_thread):
        """
            Test save functionality.
        """
        mock_load.return_value = ''
        mock_open.return_value = MagicMock()
        emitter = MagicMock()
        es = EventScheduler(emitter)

        # 0 should be in the future for a long time
        es.schedule_event('test', time.time(), None)

        es.check_state()
        self.assertEqual(emitter.emit.call_args[0][0].msg_type, 'test')
        self.assertEqual(emitter.emit.call_args[0][0].data, {})
        es.shutdown()


class TestEventSchedulerInterface(unittest.TestCase):
    def test_shutdown(self):
        def f(message):
            print('TEST FUNC')

        bus = ThreadedEventEmitter()

        es = EventSchedulerInterface('tester')
        es.set_bus(bus)
        es.set_id('id')

        # Schedule a repeating event
        es.schedule_repeating_event(f, None, 10, name='f')
        es.shutdown()

        # Check that the reference to the function has been removed from the
        # bus emitter
        self.assertTrue(len(bus.wrappers) == 0)
        self.assertTrue(len(bus._events['id:f']) == 0)
