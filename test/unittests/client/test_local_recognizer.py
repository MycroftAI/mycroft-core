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
from unittest.mock import patch

import os
from speech_recognition import WavFile

from mycroft.client.speech.listener import RecognizerLoop
from mycroft.configuration import Configuration
from test.util import base_config

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")


class PocketSphinxRecognizerTest(unittest.TestCase):
    def setUp(self):
        with patch('mycroft.configuration.Configuration.get') as \
                mock_config_get:
            conf = base_config()
            conf['hotwords']['hey mycroft']['module'] = 'pocketsphinx'
            mock_config_get.return_value = conf
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
    @patch.object(Configuration, 'get')
    def testListenerConfig(self, mock_config_get):
        """Ensure that the fallback method collecting phonemes etc.
        from the listener config works.
        """
        test_config = base_config()
        mock_config_get.return_value = test_config

        # Test "Hey Mycroft"
        rl = RecognizerLoop()
        self.assertEqual(rl.wakeword_recognizer.key_phrase, "hey mycroft")

        # Test "Hey Victoria"
        test_config['listener']['wake_word'] = 'hey victoria'
        test_config['listener']['phonemes'] = 'HH EY . V IH K T AO R IY AH'
        test_config['listener']['threshold'] = 1e-90
        rl = RecognizerLoop()
        self.assertEqual(rl.wakeword_recognizer.key_phrase, "hey victoria")

        # Test Invalid"
        test_config['listener']['wake_word'] = 'hey victoria'
        test_config['listener']['phonemes'] = 'ZZZZZZZZZZZZ'
        rl = RecognizerLoop()
        self.assertEqual(rl.wakeword_recognizer.key_phrase, "hey mycroft")

    @patch.object(Configuration, 'get')
    def testHotwordConfig(self, mock_config_get):
        """Ensure that the fallback method collecting phonemes etc.
        from the listener config works.
        """
        test_config = base_config()
        mock_config_get.return_value = test_config

        # Set fallback values
        test_config['listener']['phonemes'] = 'HH EY . V IH K T AO R IY AH'
        test_config['listener']['threshold'] = 1e-90

        steve_conf = {
            'model': 'pocketsphinx',
            'phonemes': 'S T IY V .',
            'threshold': 1e-42
        }

        test_config['hotwords']['steve'] = steve_conf
        test_config['listener']['wake_word'] = 'steve'

        rl = RecognizerLoop()
        self.assertEqual(rl.wakeword_recognizer.key_phrase, 'steve')

        # Ensure phonemes and threshold are poulated from listener config
        # if they're missing

        # Set fallback values
        test_config['listener']['phonemes'] = 'S T IY V .'
        test_config['listener']['threshold'] = 1e-90

        steve_conf = {
            'model': 'pocketsphinx'
        }

        test_config['hotwords']['steve'] = steve_conf
        test_config['listener']['wake_word'] = 'steve'
        rl = RecognizerLoop()
        self.assertEqual(rl.wakeword_recognizer.key_phrase, 'steve')
        self.assertEqual(rl.wakeword_recognizer.phonemes, 'S T IY V .')
