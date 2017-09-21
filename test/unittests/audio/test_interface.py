import unittest
from shutil import rmtree
from threading import Thread
from time import sleep

from os.path import exists

import mycroft.audio
from mycroft.util import create_signal, check_for_signal

"""
    Tests for public interface for audio interface
"""


done_waiting = False


def wait_while_speaking_thread():
    global done_waiting
    mycroft.audio.wait_while_speaking()
    done_waiting = True


class TestInterface(unittest.TestCase):
    def setUp(self):
        if exists('/tmp/mycroft'):
            rmtree('/tmp/mycroft')

    def test_is_speaking(self):
        create_signal('isSpeaking')
        self.assertTrue(mycroft.audio.is_speaking())
        # Check that the signal hasn't been removed
        self.assertTrue(check_for_signal('isSpeaking'))
        self.assertFalse(mycroft.audio.is_speaking())

    def test_wait_while_speaking(self):
        # Check that test terminates
        create_signal('isSpeaking')
        Thread(target=wait_while_speaking_thread).start()
        sleep(2)
        self.assertFalse(done_waiting)
        check_for_signal('isSpeaking')
        sleep(2)
        self.assertTrue(done_waiting)


if __name__ == "__main__":
    unittest.main()
