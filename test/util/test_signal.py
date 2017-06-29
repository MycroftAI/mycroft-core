from os.path import dirname, join, exists, isfile
import unittest
from shutil import rmtree
from mycroft.util import create_signal, check_for_signal


class TestSignals(unittest.TestCase):
    def setUp(self):
        if exists('/tmp/mycroft'):
            rmtree('/tmp/mycroft')

    def test_create_signal(self):
        create_signal('test_signal')
        self.assertTrue(isfile('/tmp/mycroft/ipc/signal/test_signal'))

    def test_check_signal(self):
        if exists('/tmp/mycroft'):
            rmtree('/tmp/mycroft')
        # check that signal is not found if file does not exist
        self.assertFalse(check_for_signal('test_signal'))

        # Check that the signal is found when created
        create_signal('test_signal')
        self.assertTrue(check_for_signal('test_signal'))
        # Check that the signal is removed after use
        self.assertFalse(isfile('/tmp/mycroft/ipc/signal/test_signal'))


if __name__ == "__main__":
    unittest.main()
