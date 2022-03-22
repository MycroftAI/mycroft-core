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
import unittest.mock as mock

from shutil import rmtree
from threading import Thread
from time import sleep

from os.path import exists

import mycroft.audio.speech as speech
from mycroft.messagebus import Message
from mycroft.tts.remote_tts import RemoteTTSTimeoutException

"""Tests for speech dispatch service."""


tts_mock = mock.Mock()


def setup_mocks(config_mock, tts_factory_mock):
    """Do the common setup for the mocks."""
    config_mock.get.return_value = {}

    tts_factory_mock.create.return_value = tts_mock
    config_mock.reset_mock()
    tts_factory_mock.reset_mock()
    tts_mock.reset_mock()


@mock.patch('mycroft.audio.speech.Configuration')
@mock.patch('mycroft.audio.speech.TTSFactory')
class TestSpeech(unittest.TestCase):
    def test_life_cycle(self, tts_factory_mock, config_mock):
        """Ensure the init and shutdown behaves as expected."""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        speech.init(bus)

        self.assertTrue(tts_factory_mock.create.called)
        bus.on.assert_any_call('mycroft.stop', speech.handle_stop)
        bus.on.assert_any_call('mycroft.audio.speech.stop',
                               speech.handle_stop)
        bus.on.assert_any_call('speak', speech.handle_speak)

        speech.shutdown()
        # TODO TTS.playback is now a singleton, this test does not reach it anymore when using mock
        #self.assertTrue(tts_mock.playback.stop.called)
        #self.assertTrue(tts_mock.playback.join.called)

    @mock.patch('mycroft.audio.speech.check_for_signal')
    def test_stop(self, check_for_signal_mock, tts_factory_mock, config_mock):
        """Ensure the stop handler signals stop correctly."""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        config_mock.get.return_value = {'tts': {'module': 'test'}}
        speech.init(bus)

        speech._last_stop_signal = 0
        check_for_signal_mock.return_value = False
        speech.handle_stop(Message('mycroft.stop'))
        self.assertEqual(speech._last_stop_signal, 0)

        check_for_signal_mock.return_value = True
        speech.handle_stop(Message('mycroft.stop'))
        self.assertNotEqual(speech._last_stop_signal, 0)


if __name__ == "__main__":
    unittest.main()
