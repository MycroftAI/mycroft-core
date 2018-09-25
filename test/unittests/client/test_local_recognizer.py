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
import mock

import os
from speech_recognition import WavFile

from mycroft.client.speech.listener import RecognizerLoop
from mycroft.configuration import Configuration
from test.util import base_config

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")


class LocalRecognizerTest(unittest.TestCase):
    def setUp(self):
        with mock.patch('mycroft.configuration.Configuration.get') as \
                mock_config_get:
            mock_config_get.return_value = base_config()
            rl = RecognizerLoop()
            self.recognizer = RecognizerLoop.create_wake_word_recognizer(rl)

    def testRecognizerWrapper(self):
        source = WavFile(os.path.join(DATA_DIR, "hey_mycroft.wav"))
        with source as audio:
            assert self.recognizer.found_wake_word(audio.stream.read())
        source = WavFile(os.path.join(DATA_DIR, "mycroft.wav"))
        with source as audio:
            assert self.recognizer.found_wake_word(audio.stream.read())

    def testRecognitionInLongerUtterance(self):
        source = WavFile(os.path.join(DATA_DIR, "weather_mycroft.wav"))
        with source as audio:
            assert self.recognizer.found_wake_word(audio.stream.read())


class LocalRecognizerInitTest(unittest.TestCase):
    @mock.patch.object(Configuration, 'get')
    def testRecognizer(self, mock_config_get):
        test_config = base_config()
        mock_config_get.return_value = test_config

        # Test "Hey Mycroft"
        rl = RecognizerLoop()
        self.assertEquals(rl.wakeword_recognizer.key_phrase, "hey mycroft")

        # Test "Hey Victoria"
        test_config['listener']['wake_word'] = 'hey victoria'
        test_config['listener']['phonemes'] = 'HH EY . V IH K T AO R IY AH'
        rl = RecognizerLoop()
        self.assertEquals(rl.wakeword_recognizer.key_phrase, "hey victoria")

        # Test Invalid"
        test_config['listener']['wake_word'] = 'hey victoria'
        test_config['listener']['phonemes'] = 'ZZZZZZZZZZZZ'
        rl = RecognizerLoop()
        self.assertEquals(rl.wakeword_recognizer.key_phrase, "hey mycroft")
