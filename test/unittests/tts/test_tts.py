from queue import Queue
import time

import unittest
from unittest import mock

import mycroft.tts

mock_phoneme = mock.Mock(name='phoneme')
mock_audio = mock.Mock(name='audio')
mock_viseme = mock.Mock(name='viseme')


class MockTTS(mycroft.tts.TTS):
    def __init__(self, lang, config, validator, audio_ext='wav',
                 phonetic_spelling=True, ssml_tags=None):
        super().__init__(lang, config, validator, audio_ext)
        self.get_tts = mock.Mock()
        self.get_tts.return_value = (mock_audio, mock_phoneme)
        self.viseme = mock.Mock()
        self.viseme.return_value = mock_viseme


class MockTTSValidator(mycroft.tts.TTSValidator):
    def validate(self):
        pass

    def validate_lang(self):
        pass

    def validate_connection(self):
        pass

    def get_tts_class(self):
        return TestTTS


class TestPlaybackThread(unittest.TestCase):
    def test_lifecycle(self):
        playback = mycroft.tts.PlaybackThread(Queue())
        playback.init(mock.Mock())
        playback.start()
        playback.stop()
        playback.join()

    @mock.patch('mycroft.tts.tts.time')
    @mock.patch('mycroft.tts.tts.play_wav')
    @mock.patch('mycroft.tts.tts.play_mp3')
    def test_process_queue(self, mock_play_mp3, mock_play_wav, mock_time):
        queue = Queue()
        playback = mycroft.tts.PlaybackThread(queue)
        mock_tts = mock.Mock()
        playback.init(mock_tts)
        playback.enclosure = mock.Mock()
        playback.start()
        try:
            # Test wav data
            wav_mock = mock.Mock(name='wav_data')
            queue.put(('wav', wav_mock, None, 0, False))
            time.sleep(0.2)
            mock_tts.begin_audio.called_with()
            mock_play_wav.assert_called_with(wav_mock, environment=None)
            mock_tts.end_audio.assert_called_with(False)

            # Test mp3 data and trigger listening True
            mp3_mock = mock.Mock(name='mp3_data')
            queue.put(('mp3', mp3_mock, None, 0, True))
            time.sleep(0.2)
            mock_play_mp3.assert_called_with(mp3_mock, environment=None)
            mock_tts.end_audio.assert_called_with(True)
            self.assertFalse(playback.enclosure.get.called)

            # Test sending visemes
            mock_time.return_value = 1234
            visemes = mock.Mock(name='visemes')
            queue.put(('mp3', mp3_mock, visemes, 0, True))
            time.sleep(0.2)
            playback.enclosure.mouth_viseme.assert_called_with(1234, visemes)

        finally:
            # Terminate the thread
            playback.stop()
            playback.join()


@mock.patch('mycroft.tts.tts.PlaybackThread')
class TestTTS(unittest.TestCase):
    def test_execute(self, mock_playback_thread):
        tts = MockTTS("en-US", {}, MockTTSValidator(None))
        bus_mock = mock.Mock()
        tts.init(bus_mock)
        self.assertTrue(tts.bus is bus_mock)

        tts.queue = mock.Mock()
        with mock.patch('mycroft.tts.tts.open') as mock_open:
            tts.execute('Oh no, not again', 42)
        self.assertTrue(tts.get_tts.called)
        tts.queue.put.assert_called_with(('wav', mock_audio, mock_viseme,
                                         42, False))

    @mock.patch('mycroft.tts.tts.open')
    def test_phoneme_cache(self, mock_open, _):
        tts = MockTTS("en-US", {}, MockTTSValidator(None))
        mock_context = mock.Mock(name='context')
        mock_file = mock.MagicMock(name='file')
        mock_open.return_value = mock_file
        mock_file.__enter__.return_value = mock_context

        phonemes = mock.Mock()
        # Test save phonemes
        tts.save_phonemes('abc', phonemes)
        mock_context.write.assert_called_with(phonemes)

        # Test load phonemes
        mock_context.read.return_value = 'phonemes '
        read_phonemes = tts.load_phonemes('abc')
        self.assertEqual(read_phonemes, None)
        with mock.patch('mycroft.tts.tts.os.path.exists') as _:
            read_phonemes = tts.load_phonemes('abc')
            self.assertEqual(read_phonemes, 'phonemes')  # assert stripped

    def test_ssml_support(self, _):
        sentence = "<speak>Prosody can be used to change the way words " \
                   "sound. The following words are " \
                   "<prosody volume='x-loud'> " \
                   "quite a bit louder than the rest of this passage. " \
                   "</prosody> Each morning when I wake up, " \
                   "<prosody rate='x-slow'>I speak quite slowly and " \
                   "deliberately until I have my coffee.</prosody> I can " \
                   "also change the pitch of my voice using prosody. " \
                   "Do you like <prosody pitch='+5%'> speech with a pitch " \
                   "that is higher, </prosody> or <prosody pitch='-10%'> " \
                   "is a lower pitch preferable?</prosody></speak>"
        sentence_no_ssml = "Prosody can be used to change the way " \
                           "words sound. The following words are quite " \
                           "a bit louder than the rest of this passage. " \
                           "Each morning when I wake up, I speak quite " \
                           "slowly and deliberately until I have my " \
                           "coffee. I can also change the pitch of my " \
                           "voice using prosody. Do you like speech " \
                           "with a pitch that is higher, or is " \
                           "a lower pitch preferable?"
        sentence_bad_ssml = "<foo_invalid>" + sentence + \
                            "</foo_invalid end=whatever>"
        sentence_extra_ssml = "<whispered>whisper tts<\\whispered>"

        tts = MockTTS("en-US", {}, MockTTSValidator(None))

        # test valid ssml
        tts.ssml_tags = ['speak', 'prosody']
        self.assertEqual(tts.validate_ssml(sentence), sentence)

        # test extra ssml
        tts.ssml_tags = ['whispered']
        self.assertEqual(tts.validate_ssml(sentence_extra_ssml),
                         sentence_extra_ssml)

        # test unsupported extra ssml
        tts.ssml_tags = ['speak', 'prosody']
        self.assertEqual(tts.validate_ssml(sentence_extra_ssml),
                         "whisper tts")

        # test mixed valid / invalid ssml
        tts.ssml_tags = ['speak', 'prosody']
        self.assertEqual(tts.validate_ssml(sentence_bad_ssml), sentence)

        # test unsupported ssml
        tts.ssml_tags = []
        self.assertEqual(tts.validate_ssml(sentence), sentence_no_ssml)

        self.assertEqual(tts.validate_ssml(sentence_bad_ssml),
                         sentence_no_ssml)

        self.assertEqual(mycroft.tts.TTS.remove_ssml(sentence),
                         sentence_no_ssml)

    def test_load_spellings(self, _):
        """Check that the spelling dictionary gets loaded."""
        tts = MockTTS("en-US", {}, MockTTSValidator(None))
        self.assertTrue(tts.spellings != {})

    def test_load_spelling_missing(self, _):
        """Test that a missing phonetic spelling dictionary counts as empty."""
        tts = MockTTS("as-DF", {}, MockTTSValidator(None))
        self.assertTrue(tts.spellings == {})


class TestTTSFactory(unittest.TestCase):
    @mock.patch('mycroft.tts.tts.Configuration')
    def test_create(self, mock_config):
        config = {
            'tts': {
                'module': 'mock'
            }
        }

        mock_config.get.return_value = config
        mock_mimic = mock.Mock(name='Mimic')
        mock_mimic_instance = mock.Mock(name='mimic')
        mock_mimic.return_value = mock_mimic_instance

        mock_tts_class = mock.Mock()
        mock_tts_instance = mock.Mock()
        mock_tts_class.return_value = mock_tts_instance

        mycroft.tts.TTSFactory.CLASSES['mimic'] = mock_mimic
        mycroft.tts.TTSFactory.CLASSES['mock'] = mock_tts_class

        # Check that correct module is selected
        tts_instance = mycroft.tts.TTSFactory.create()
        self.assertEqual(tts_instance, mock_tts_instance)

        # Assert falling back to mimic if load fails
        def side_effect(*args):
            raise Exception

        mock_tts_class.side_effect = side_effect
        tts_instance = mycroft.tts.TTSFactory.create()
        self.assertEqual(tts_instance, mock_mimic_instance)

        # Make sure exception is raised when mimic fails
        mock_mimic.side_effect = side_effect
        config['tts']['module'] = 'mimic'
        with self.assertRaises(Exception):
            tts_instance = mycroft.tts.TTSFactory.create()
