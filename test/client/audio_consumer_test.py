import unittest
from Queue import Queue

from os.path import dirname, join
from speech_recognition import WavFile, AudioData
from mycroft.client.speech.listener import (
    WakewordExtractor,
    AudioConsumer,
    RecognizerLoop
)
from mycroft.client.speech.recognizer_wrapper import (
    RemoteRecognizerWrapperFactory
)


__author__ = 'seanfitz'


class MockRecognizer(object):
    def __init__(self, transcription=None):
        self.transcriptions = []

    def recognize_google(self, audio, key=None, language=None, show_all=False):
        return self.tanscriptions.pop(0)

    def set_transcriptions(self, transcriptions):
        self.tanscriptions = transcriptions


class AudioConsumerTest(unittest.TestCase):
    """
    AudioConsumerTest
    """

    def setUp(self):
        self.loop = RecognizerLoop()
        self.queue = Queue()
        self.recognizer = MockRecognizer()

        self.consumer = AudioConsumer(
            self.loop.state,
            self.queue,
            self.loop,
            self.loop.wakeup_recognizer,
            self.loop.mycroft_recognizer,
            RemoteRecognizerWrapperFactory.wrap_recognizer(
                self.recognizer, 'google'))

    def __create_sample_from_test_file(self, sample_name):
        root_dir = dirname(dirname(dirname(__file__)))
        filename = join(
            root_dir, 'test', 'client', 'data', sample_name + '.wav')
        wavfile = WavFile(filename)
        with wavfile as source:
            return AudioData(
                source.stream.read(), wavfile.SAMPLE_RATE,
                wavfile.SAMPLE_WIDTH)

    def test_audio_pos_front_back(self):
        audio = self.__create_sample_from_test_file('mycroft_in_utterance')
        self.queue.put(audio)
        TRUE_POS_BEGIN = 69857 + int(
            WakewordExtractor.TRIM_SECONDS * audio.sample_rate *
            audio.sample_width)
        TRUE_POS_END = 89138 - int(
            WakewordExtractor.TRIM_SECONDS * audio.sample_rate *
            audio.sample_width)

        TOLERANCE_RANGE_FRAMES = (
            WakewordExtractor.MAX_ERROR_SECONDS * audio.sample_rate *
            audio.sample_width)

        monitor = {}
        self.recognizer.set_transcriptions(
            ["what's the weather next week", ""])

        def wakeword_callback(message):
            monitor['pos_begin'] = message.get('pos_begin')
            monitor['pos_end'] = message.get('pos_end')

        self.loop.once('recognizer_loop:wakeword', wakeword_callback)
        self.consumer.read_audio()

        pos_begin = monitor.get('pos_begin')
        self.assertIsNotNone(pos_begin)
        diff = abs(pos_begin - TRUE_POS_BEGIN)
        self.assertTrue(
            diff <= TOLERANCE_RANGE_FRAMES,
            str(diff) + " is not less than " + str(TOLERANCE_RANGE_FRAMES))

        pos_end = monitor.get('pos_end')
        self.assertIsNotNone(pos_end)
        diff = abs(pos_end - TRUE_POS_END)
        self.assertTrue(
            diff <= TOLERANCE_RANGE_FRAMES,
            str(diff) + " is not less than " + str(TOLERANCE_RANGE_FRAMES))

    def test_wakeword_in_beginning(self):
        self.queue.put(self.__create_sample_from_test_file('mycroft'))
        monitor = {}
        self.recognizer.set_transcriptions([
            "what's the weather next week", ""])

        def callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', callback)
        self.consumer.read_audio()
        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEquals("what's the weather next week", utterances[0])

    def test_wakeword_in_phrase(self):
        self.queue.put(self.__create_sample_from_test_file('mycroft'))
        monitor = {}
        self.recognizer.set_transcriptions([
            "he can do other stuff too", "what's the weather in cincinnati"])

        def callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:utterance', callback)
        self.consumer.read_audio()
        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 2)
        self.assertEquals("he can do other stuff too", utterances[0])
        self.assertEquals("what's the weather in cincinnati", utterances[1])

    def test_call_and_response(self):
        self.queue.put(self.__create_sample_from_test_file('mycroft'))
        monitor = {}
        self.recognizer.set_transcriptions(["mycroft", ""])

        def wakeword_callback(message):
            monitor['wakeword'] = message.get('utterance')

        def utterance_callback(message):
            monitor['utterances'] = message.get('utterances')

        self.loop.once('recognizer_loop:wakeword', wakeword_callback)
        self.consumer.read_audio()

        self.assertIsNotNone(monitor.get('wakeword'))

        self.queue.put(self.__create_sample_from_test_file('mycroft'))
        self.recognizer.set_transcriptions(
            ["what's the weather next week", ""])
        self.loop.once('recognizer_loop:utterance', utterance_callback)
        self.consumer.read_audio()

        utterances = monitor.get('utterances')
        self.assertIsNotNone(utterances)
        self.assertTrue(len(utterances) == 1)
        self.assertEquals("what's the weather next week", utterances[0])

    def test_ignore_wakeword_when_sleeping(self):
        self.queue.put(self.__create_sample_from_test_file('mycroft'))
        self.loop.sleep()
        monitor = {}
        self.recognizer.set_transcriptions(["", ""])

        def wakeword_callback(message):
            monitor['wakeword'] = message.get('utterance')

        self.loop.once('recognizer_loop:wakeword', wakeword_callback)
        self.consumer.read_audio()

        self.assertIsNone(monitor.get('wakeword'))
        self.assertTrue(self.loop.state.sleeping)
