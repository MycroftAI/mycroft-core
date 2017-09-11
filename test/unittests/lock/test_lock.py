from os.path import dirname, join, exists, isfile
import os
import signal
import unittest
import mock
from shutil import rmtree
from mycroft.lock import Lock


class TestLock(unittest.TestCase):
    def setUp(self):
        if exists('/tmp/mycroft'):
            rmtree('/tmp/mycroft')

    def test_create_lock(self):
        l1 = Lock('test')
        self.assertTrue(isfile('/tmp/mycroft/test.pid'))

    def test_delete_lock(self):
        l1 = Lock('test')
        self.assertTrue(isfile('/tmp/mycroft/test.pid'))
        l1.delete()
        self.assertFalse(isfile('/tmp/mycroft/test.pid'))

    @mock.patch('os.kill')
    def test_existing_lock(self, mock_kill):
        """ Test that an existing lock will kill the old pid. """
        l1 = Lock('test')
        self.assertTrue(isfile('/tmp/mycroft/test.pid'))
        l2 = Lock('test2')
        self.assertFalse(mock_kill.called)
        l2 = Lock('test')
        self.assertTrue(mock_kill.called)

    def test_keyboard_interrupt(self):
        l1 = Lock('test')
        self.assertTrue(isfile('/tmp/mycroft/test.pid'))
        try:
            os.kill(os.getpid(), signal.SIGINT)
        except KeyboardInterrupt:
            pass
        self.assertFalse(isfile('/tmp/mycroft/test.pid'))


if __name__ == '__main__':
    unittest.main()
