from speech_recognition import WavFile
import os

from mycroft.client.speech import wakeword_recognizer

import unittest


__author__ = 'seanfitz'

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")


class WakewordRecognizerTest(unittest.TestCase):
    def setUp(self):
        self.ww_recognizer = wakeword_recognizer.create_recognizer()

    def testRecognizerWrapper(self):
        source = WavFile(os.path.join(DATA_DIR, "hey_mycroft.wav"))
        with source as audio:
            hyp = self.ww_recognizer.transcribe(audio.stream.read())
            assert hyp.hypstr.lower() == "hey mycroft"
        source = WavFile(os.path.join(DATA_DIR, "mycroft.wav"))
        with source as audio:
            hyp = self.ww_recognizer.transcribe(audio.stream.read())
            assert hyp.hypstr.lower() == "hey mycroft"

    def testRecognitionInLongerUtterance(self):
        source = WavFile(os.path.join(DATA_DIR, "mycroft_in_utterance.wav"))
        with source as audio:
            hyp = self.ww_recognizer.transcribe(audio.stream.read())
            assert hyp.hypstr.lower() == "hey mycroft"
