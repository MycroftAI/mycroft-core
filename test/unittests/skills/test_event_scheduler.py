"""
    Test cases regarding the event scheduler.
"""

import unittest
import mock
import time

from mycroft.skills.event_scheduler import EventScheduler


class TestEventScheduler(unittest.TestCase):
    @mock.patch('threading.Thread')
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('mycroft.skills.event_scheduler.open')
    def test_create(self, mock_open, mock_json_dump, mock_load, mock_thread):
        """
            Test creating and shutting down event_scheduler.
        """
        mock_load.return_value = ''
        mock_open.return_value = mock.MagicMock()
        emitter = mock.MagicMock()
        es = EventScheduler(emitter)
        es.shutdown()
        self.assertEquals(mock_json_dump.call_args[0][0], {})

    @mock.patch('threading.Thread')
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('mycroft.skills.event_scheduler.open')
    def test_add_remove(self, mock_open, mock_json_dump,
                        mock_load, mock_thread):
        """
            Test add an event and then remove it.
        """
        # Thread start is mocked so will not actually run the thread loop
        mock_load.return_value = ''
        mock_open.return_value = mock.MagicMock()
        emitter = mock.MagicMock()
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

    @mock.patch('threading.Thread')
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('mycroft.skills.event_scheduler.open')
    def test_save(self, mock_open, mock_dump, mock_load, mock_thread):
        """
            Test save functionality.
        """
        mock_load.return_value = ''
        mock_open.return_value = mock.MagicMock()
        emitter = mock.MagicMock()
        es = EventScheduler(emitter)

        # 900000000000 should be in the future for a long time
        es.schedule_event('test', 900000000000, None)
        es.schedule_event('test-repeat', 910000000000, 60)
        es.check_state()

        es.shutdown()

        # Make sure the dump method wasn't called with test-repeat
        self.assertEquals(mock_dump.call_args[0][0],
                          {'test': [(900000000000, None, {})]})

    @mock.patch('threading.Thread')
    @mock.patch('json.load')
    @mock.patch('json.dump')
    @mock.patch('mycroft.skills.event_scheduler.open')
    def test_send_event(self, mock_open, mock_dump, mock_load, mock_thread):
        """
            Test save functionality.
        """
        mock_load.return_value = ''
        mock_open.return_value = mock.MagicMock()
        emitter = mock.MagicMock()
        es = EventScheduler(emitter)

        # 0 should be in the future for a long time
        es.schedule_event('test', time.time(), None)

        es.check_state()
        self.assertEquals(emitter.emit.call_args[0][0].type, 'test')
        self.assertEquals(emitter.emit.call_args[0][0].data, {})
        es.shutdown()
