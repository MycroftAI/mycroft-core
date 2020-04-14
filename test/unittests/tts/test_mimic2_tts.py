import unittest
from unittest import mock

from mycroft.tts.mimic2_tts import Mimic2
from mycroft.tts.remote_tts import RemoteTTSException


@mock.patch('mycroft.tts.mimic2_tts.FuturesSession')
@mock.patch('mycroft.tts.tts.PlaybackThread')
class TestMimic2(unittest.TestCase):
    def test_get_tts(self, _, mock_session):
        mock_session_instance = mock.Mock(name='SessionMock')
        mock_session.return_value = mock_session_instance

        get_mock = mock.Mock(name='getMock')
        mock_session_instance.get.return_value = get_mock

        result_mock = mock.Mock(name='resultMock')
        get_mock.result.return_value = result_mock
        result_mock.json.return_value = {'audio_base64': '', 'visimes': ''}
        result_mock.status_code = 200
        m2 = Mimic2('en-US', {'url': 'https://just.testing.nu'})

        with mock.patch('mycroft.tts.mimic2_tts.open') as mock_open:
            wav_file, vis = m2.get_tts("Hello old friend", 'test.wav')
        self.assertTrue(mock_session_instance.get.called)

    def test_get_tts_backend_error(self, _, mock_session):
        mock_session_instance = mock.Mock(name='SessionMock')
        mock_session.return_value = mock_session_instance

        get_mock = mock.Mock(name='getMock')
        mock_session_instance.get.return_value = get_mock

        result_mock = mock.Mock(name='resultMock')
        get_mock.result.return_value = result_mock
        result_mock.json.return_value = ''
        result_mock.status_code = 500

        m2 = Mimic2('en-US', {'url': 'https://just.testing.nu'})
        with self.assertRaises(RemoteTTSException):
            with mock.patch('mycroft.tts.mimic2_tts.open') as mock_open:
                wav_file, vis = m2.get_tts("Hello old friend", 'test.wav')

    def test_visemes(self, _, __):
        m2 = Mimic2('en-US', {'url': 'https://just.testing.nu'})
        phonemes = [('pau', 0.137), ('hh', 0.236), ('ax', 0.286), ('l', 0.387),
                    ('ow', 0.542), ('f', 0.642), ('r', 0.728), ('eh', 0.807),
                    ('n', 0.899), ('d', 1.033), ('pau', 1.187)]
        vis = m2.viseme(phonemes)
        self.assertEqual(vis, [('4', 0.137), ('0', 0.236), ('0', 0.286),
                               ('3', 0.387), ('2', 0.542), ('5', 0.642),
                               ('2', 0.728), ('0', 0.807), ('3', 0.899),
                               ('3', 1.033), ('4', 1.187)])

    def test_preprocess(self, _, __):
        """Test mimic2 specific preprocessing.

        The Mimic-2 backend has some specifics regarding how the sentence
        must look to render correctly.
        """
        m2 = Mimic2('en-US', {'url': 'https://just.testing.nu'})
        # Test short sentence get's '.' at the end.
        self.assertEqual(m2._preprocess_sentence('Hello old friend'),
                         ['Hello old friend.'])
        # Ensure that a very long sentence gets separated into chunks.
        self.assertEqual(m2._preprocess_sentence('Harris said he felt such '
                                                 'extraordinary fits of '
                                                 'giddiness come over him at '
                                                 'times, that he hardly knew '
                                                 'what he was doing; and then '
                                                 'George said that he had '
                                                 'fits of giddiness too, and '
                                                 'hardly knew what he was '
                                                 'doing.'),
                         ['Harris said he felt such extraordinary fits of '
                          'giddiness come over him at times, that he hardly '
                          'knew what he was doing.',
                          'and then George said that he had fits of giddiness '
                          'too, and hardly knew what he was doing.'])

    @mock.patch('mycroft.tts.mimic2_tts.open')
    def test_phoneme_cache(self, mock_open, _, __):
        m2 = Mimic2('en-US', {'url': 'https://just.testing.nu'})
        phonemes = [['pau', 0.137], ['hh', 0.236], ['ax', 0.286], ['l', 0.387],
                    ['ow', 0.542], ['f', 0.642], ['r', 0.728], ['eh', 0.807],
                    ['n', 0.899], ['d', 1.033], ['pau', 1.187]]

        mock_context = mock.Mock(name='context')
        mock_file = mock.MagicMock(name='file')
        mock_open.return_value = mock_file
        mock_file.__enter__.return_value = mock_context
        m2.save_phonemes('abc', phonemes)
        self.assertTrue(mock_context.write.called_with)
        with mock.patch('mycroft.tts.mimic2_tts.json.load') as mock_load:
            read_phonemes = m2.load_phonemes('abc')
            self.assertEqual(read_phonemes, None)
            mock_load.reset_mock()
            with mock.patch('mycroft.tts.mimic2_tts.os.path.exists') as _:
                mock_load.return_value = phonemes
                read_phonemes = m2.load_phonemes('abc')
                self.assertEqual(read_phonemes, phonemes)
