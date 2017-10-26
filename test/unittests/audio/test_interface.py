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
