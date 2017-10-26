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
import signal
import unittest
from shutil import rmtree

import mock
import os
from os.path import exists, isfile

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
