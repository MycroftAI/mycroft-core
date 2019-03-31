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

from os.path import exists, isfile, join
from tempfile import gettempdir

from mycroft.util import create_signal, check_for_signal


class TestSignals(unittest.TestCase):
    def setUp(self):
        if exists(join(gettempdir(), 'mycroft')):
            rmtree(join(gettempdir(), 'mycroft'))

    def test_create_signal(self):
        create_signal('test_signal')
        self.assertTrue(isfile(join(gettempdir(),
                                    'mycroft/ipc/signal/test_signal')))

    def test_check_signal(self):
        if exists(join(gettempdir(), 'mycroft')):
            rmtree(join(gettempdir(), 'mycroft'))
        # check that signal is not found if file does not exist
        self.assertFalse(check_for_signal('test_signal'))

        # Check that the signal is found when created
        create_signal('test_signal')
        self.assertTrue(check_for_signal('test_signal'))
        # Check that the signal is removed after use
        self.assertFalse(isfile(join(gettempdir(),
                                     'mycroft/ipc/signal/test_signal')))


if __name__ == "__main__":
    unittest.main()
