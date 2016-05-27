import unittest

import os
from speech_recognition import WavFile

from mycroft.client.speech.local_recognizer import LocalRecognizer

__author__ = 'seanfitz'

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")


class LocalRecognizerTest(unittest.TestCase):
    def setUp(self):
        self.recognizer = LocalRecognizer()

    def testRecognizerWrapper(self):
        source = WavFile(os.path.join(DATA_DIR, "hey_mycroft.wav"))
        with source as audio:
            hyp = self.recognizer.transcribe(audio.stream.read())
            assert "mycroft" in hyp.hypstr.lower()
        source = WavFile(os.path.join(DATA_DIR, "mycroft.wav"))
        with source as audio:
            hyp = self.recognizer.transcribe(audio.stream.read())
            assert "mycroft" in hyp.hypstr.lower()

    def testRecognitionInLongerUtterance(self):
        source = WavFile(os.path.join(DATA_DIR, "weather_mycroft.wav"))
        with source as audio:
            hyp = self.recognizer.transcribe(audio.stream.read())
            assert "mycroft" in hyp.hypstr.lower()
