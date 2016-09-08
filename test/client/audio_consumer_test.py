# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import unittest
from Queue import Queue

import speech_recognition
from os.path import dirname, join
from speech_recognition import WavFile, AudioData

from mycroft.client.speech.listener import AudioConsumer, RecognizerLoop
from mycroft.client.speech.local_recognizer import LocalRecognizer
from mycroft.stt import GoogleSTT

__author__ = 'seanfitz'


class MockRecognizer(object):
    def __init__(self):
        self.transcriptions = []

    def recognize_google(self, audio, key=None, language=None, show_all=False):
        if len(self.transcriptions) > 0:
            return self.transcriptions.pop(0)
        else:
            raise speech_recognition.UnknownValueError()

    def set_transcriptions(self, transcriptions):
        self.transcriptions = transcriptions


class AudioConsumerTest(unittest.TestCase):
    """
    AudioConsumerTest
    """

    def setUp(self):
        self.loop = RecognizerLoop()
        self.queue = Queue()
        self.recognizer = MockRecognizer()

        self.consumer = AudioConsumer(
            self.loop.state, self.queue, self.loop, GoogleSTT(),
            LocalRecognizer(self.loop.wakeup_recognizer.key_phrase,
                            self.loop.wakeup_recognizer.phonemes, "1e-16"),
            self.loop.mycroft_recognizer)

    def __create_sample_from_test_file(self, sample_name):
        root_dir = dirname(dirname(dirname(__file__)))
        filename = join(
            root_dir, 'test', 'client', 'data', sample_name + '.wav')
        wavfile = WavFile(filename)
        with wavfile as source:
            return AudioData(
                source.stream.read(), wavfile.SAMPLE_RATE,
                wavfile.SAMPLE_WIDTH)

    def test_word_extraction(self):
        """
        This is intended to test the extraction of the word: ``mycroft``.
        The values for ``ideal_begin`` and ``ideal_end`` were found using an
        audio tool like Audacity and they represent a sample value position of
        the audio. ``tolerance`` is an acceptable margin error for the distance
        between the ideal and actual values found by the ``WordExtractor``
        """

        # TODO: implement WordExtractor test without relying on the listener
        return

        audio = self.__create_sample_from_test_file('weather_mycroft')
        self.queue.put(audio)
        tolerance = 4000
        ideal_begin = 70000
        ideal_end = 92000

        monitor = {}
        self.recognizer.set_transcriptions(["what's the weather next week"])

        def wakeword_callback(message):
            monitor['pos_begin'] = message.get('pos_begin')
            monitor['pos_end'] = message.get('pos_end')

        self.loop.once('recognizer_loop:wakeword', wakeword_callback)
        self.consumer.read_audio()

        actual_begin = monitor.get('pos_begin')
        self.assertIsNotNone(actual_begin)
        diff = abs(actual_begin - ideal_begin)
        self.assertTrue(
            diff <= tolerance,
            str(diff) + " is not less than " + str(tolerance))

        actual_end = monitor.get('pos_end')
        self.assertIsNotNone(actual_end)
        diff = abs(actual_end - ideal_end)
        self.assertTrue(
            diff <= tolerance,
            str(diff) + " is not less than " + str(tolerance))

    def test_wakeword_in_beginning(self):
        self.queue.put(self.__create_sample_from_test_file('weather_mycroft'))
        self.recognizer.set_transcriptions(["what's the weather next week"])
        monitor = {}

        def callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', callback)
        self.consumer.read_audio()

        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEquals("what's the weather next week", utterances[0])

    def test_wakeword(self):
        self.queue.put(self.__create_sample_from_test_file('mycroft'))
        self.recognizer.set_transcriptions(["silence"])
        monitor = {}

        def callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', callback)
        self.consumer.read_audio()

        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEquals("silence", utterances[0])

    def test_ignore_wakeword_when_sleeping(self):
        self.queue.put(self.__create_sample_from_test_file('mycroft'))
        self.recognizer.set_transcriptions(["not detected"])
        self.loop.sleep()
        monitor = {}

        def wakeword_callback(message):
            monitor['wakeword'] = message.get('utterance')

        self.loop.once('recognizer_loop:wakeword', wakeword_callback)
        self.consumer.read_audio()
        self.assertIsNone(monitor.get('wakeword'))
        self.assertTrue(self.loop.state.sleeping)

    def test_wakeup(self):
        self.queue.put(self.__create_sample_from_test_file('mycroft_wakeup'))
        self.loop.sleep()
        self.consumer.read_audio()
        self.assertFalse(self.loop.state.sleeping)

    def test_stop(self):
        self.queue.put(self.__create_sample_from_test_file('mycroft'))
        self.consumer.read_audio()

        self.queue.put(self.__create_sample_from_test_file('stop'))
        self.recognizer.set_transcriptions(["stop"])
        monitor = {}

        def utterance_callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', utterance_callback)
        self.consumer.read_audio()

        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEquals("stop", utterances[0])

    def test_record(self):
        self.queue.put(self.__create_sample_from_test_file('mycroft'))
        self.consumer.read_audio()

        self.queue.put(self.__create_sample_from_test_file('record'))
        self.recognizer.set_transcriptions(["record"])
        monitor = {}

        def utterance_callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', utterance_callback)
        self.consumer.read_audio()

        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEquals("record", utterances[0])
