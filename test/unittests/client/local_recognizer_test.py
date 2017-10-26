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

import os
from speech_recognition import WavFile

from mycroft.client.speech.listener import RecognizerLoop


DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")


class LocalRecognizerTest(unittest.TestCase):
    def setUp(self):
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
