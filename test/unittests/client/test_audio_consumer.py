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

import speech_recognition
from os.path import dirname, join
from speech_recognition import WavFile, AudioData

from mycroft.client.speech.listener import (AudioConsumer, RecognizerLoop,
                                            AUDIO_DATA, STREAM_START,
                                            STREAM_DATA, STREAM_STOP)
from mycroft.stt import MycroftSTT
from queue import Queue


class MockRecognizer(object):
    def __init__(self):
        self.transcriptions = []

    def recognize_mycroft(self, audio, key=None,
                          language=None, show_all=False):
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
            self.loop.state, self.queue, self.loop, MycroftSTT(),
            self.loop.wakeup_recognizer,
            self.loop.wakeword_recognizer)

    def __create_sample_from_test_file(self, sample_name):
        root_dir = dirname(dirname(dirname(__file__)))
        filename = join(
            root_dir, 'unittests', 'client',
            'data', sample_name + '.wav')
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
        self.queue.put((AUDIO_DATA, audio))
        tolerance = 4000
        ideal_begin = 70000
        ideal_end = 92000

        monitor = {}
        self.recognizer.set_transcriptions(["what's the weather next week"])

        def wakeword_callback(message):
            monitor['pos_begin'] = message.get('pos_begin')
            monitor['pos_end'] = message.get('pos_end')

        self.loop.once('recognizer_loop:wakeword', wakeword_callback)
        self.consumer.read()

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

    @unittest.skip('Disabled while unittests are brought upto date')
    def test_wakeword_in_beginning(self):
        tag = AUDIO_DATA
        data = self.__create_sample_from_test_file('weather_mycroft')
        self.queue.put((tag, data))
        self.recognizer.set_transcriptions(["what's the weather next week"])
        monitor = {}

        def callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', callback)
        self.consumer.read()

        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEqual("what's the weather next week", utterances[0])

    @unittest.skip('Disabled while unittests are brought upto date')
    def test_wakeword(self):
        self.queue.put((AUDIO_DATA,
                        self.__create_sample_from_test_file('mycroft')))
        self.recognizer.set_transcriptions(["silence"])
        monitor = {}

        def callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', callback)
        self.consumer.read()

        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEqual("silence", utterances[0])

    def test_ignore_wakeword_when_sleeping(self):
        self.queue.put((AUDIO_DATA,
                        self.__create_sample_from_test_file('mycroft')))
        self.recognizer.set_transcriptions(["not detected"])
        self.loop.sleep()
        monitor = {}

        def wakeword_callback(message):
            monitor['wakeword'] = message.get('utterance')

        self.loop.once('recognizer_loop:wakeword', wakeword_callback)
        self.consumer.read()
        self.assertIsNone(monitor.get('wakeword'))
        self.assertTrue(self.loop.state.sleeping)

    def test_wakeup(self):
        tag = AUDIO_DATA
        data = self.__create_sample_from_test_file('mycroft_wakeup')
        self.queue.put((tag, data))
        self.loop.sleep()
        self.consumer.read()
        self.assertFalse(self.loop.state.sleeping)

    @unittest.skip('Disabled while unittests are brought upto date')
    def test_stop(self):
        self.queue.put((AUDIO_DATA,
                        self.__create_sample_from_test_file('mycroft')))
        self.consumer.read()

        self.queue.put((AUDIO_DATA,
                        self.__create_sample_from_test_file('stop')))
        self.recognizer.set_transcriptions(["stop"])
        monitor = {}

        def utterance_callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', utterance_callback)
        self.consumer.read()

        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEqual("stop", utterances[0])

    @unittest.skip('Disabled while unittests are brought upto date')
    def test_record(self):
        self.queue.put((AUDIO_DATA,
                        self.__create_sample_from_test_file('mycroft')))
        self.consumer.read()

        self.queue.put((AUDIO_DATA,
                        self.__create_sample_from_test_file('record')))
        self.recognizer.set_transcriptions(["record"])
        monitor = {}

        def utterance_callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', utterance_callback)
        self.consumer.read()

        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEqual("record", utterances[0])
