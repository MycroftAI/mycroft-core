import unittest

import os
from speech_recognition import WavFile

from mycroft.client.speech.listener import RecognizerLoop

__author__ = 'seanfitz'

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
