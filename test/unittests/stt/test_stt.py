import mock
import unittest
import mycroft.stt
from mycroft.configuration import ConfigurationManager


class TestSTT(unittest.TestCase):
    @mock.patch.object(ConfigurationManager, 'get')
    def test_factory(self, mock_get):
        mycroft.stt.STTApi = mock.MagicMock()

        config = {'stt': {
                 'module': 'mycroft',
                 'wit': {'credential': {'token': 'FOOBAR'}},
                 'google': {'credential': {'token': 'FOOBAR'}},
                 'ibm': {'credential': {'token': 'FOOBAR'}},
                 'kaldi': {'uri': 'https://test.com'},
                 'mycroft': {'uri': 'https://test.com'}
            },
            'lang': 'en-US'
        }
        mock_get.return_value = config

        stt = mycroft.stt.STTFactory.create()
        self.assertEquals(type(stt), mycroft.stt.MycroftSTT)

        config['stt']['module'] = 'google'
        stt = mycroft.stt.STTFactory.create()
        self.assertEquals(type(stt), mycroft.stt.GoogleSTT)

        config['stt']['module'] = 'ibm'
        stt = mycroft.stt.STTFactory.create()
        self.assertEquals(type(stt), mycroft.stt.IBMSTT)

        config['stt']['module'] = 'kaldi'
        stt = mycroft.stt.STTFactory.create()
        self.assertEquals(type(stt), mycroft.stt.KaldiSTT)

        config['stt']['module'] = 'wit'
        stt = mycroft.stt.STTFactory.create()
        self.assertEquals(type(stt), mycroft.stt.WITSTT)

    @mock.patch.object(ConfigurationManager, 'get')
    def test_stt(self, mock_get):
        mycroft.stt.STTApi = mock.MagicMock()
        config = {'stt': {
                 'module': 'mycroft',
                 'mycroft': {'uri': 'https://test.com'}
            },
            'lang': 'en-US'
        }
        mock_get.return_value = config

        class TestSTT(mycroft.stt.STT):
            def execute(self, audio, language=None):
                pass

        stt = TestSTT()
        self.assertEqual(stt.lang, 'en-US')
        config['lang'] = 'en-us'

        # Check that second part of lang gets capitalized
        stt = TestSTT()
        self.assertEqual(stt.lang, 'en-US')

        # Check that it works with two letters
        config['lang'] = 'sv'
        stt = TestSTT()
        self.assertEqual(stt.lang, 'sv')

    @mock.patch.object(ConfigurationManager, 'get')
    def test_mycroft_stt(self, mock_get):
        mycroft.stt.STTApi = mock.MagicMock()
        config = {'stt': {
                 'module': 'mycroft',
                 'mycroft': {'uri': 'https://test.com'}
            },
            'lang': 'en-US'
        }
        mock_get.return_value = config

        stt = mycroft.stt.MycroftSTT()
        audio = mock.MagicMock()
        stt.execute(audio, 'en-us')
        self.assertTrue(mycroft.stt.STTApi.called)

    @mock.patch.object(ConfigurationManager, 'get')
    def test_google_stt(self, mock_get):
        mycroft.stt.Recognizer = mock.MagicMock
        config = {'stt': {
                 'module': 'google',
                 'google': {'credential': {'token': 'FOOBAR'}},
            },
            "lang": "en-US"
        }
        mock_get.return_value = config

        audio = mock.MagicMock()
        stt = mycroft.stt.GoogleSTT()
        stt.execute(audio)
        self.assertTrue(stt.recognizer.recognize_google.called)

    @mock.patch.object(ConfigurationManager, 'get')
    def test_ibm_stt(self, mock_get):
        mycroft.stt.Recognizer = mock.MagicMock
        config = {'stt': {
                 'module': 'ibm',
                 'ibm': {'credential': {'token': 'FOOBAR'}},
            },
            "lang": "en-US"
        }
        mock_get.return_value = config

        audio = mock.MagicMock()
        stt = mycroft.stt.IBMSTT()
        stt.execute(audio)
        self.assertTrue(stt.recognizer.recognize_ibm.called)

    @mock.patch.object(ConfigurationManager, 'get')
    def test_wit_stt(self, mock_get):
        mycroft.stt.Recognizer = mock.MagicMock
        config = {'stt': {
                 'module': 'wit',
                 'wit': {'credential': {'token': 'FOOBAR'}},
            },
            "lang": "en-US"
        }
        mock_get.return_value = config

        audio = mock.MagicMock()
        stt = mycroft.stt.WITSTT()
        stt.execute(audio)
        self.assertTrue(stt.recognizer.recognize_wit.called)

    @mock.patch('mycroft.stt.post')
    @mock.patch.object(ConfigurationManager, 'get')
    def test_kaldi_stt(self, mock_get, mock_post):
        mycroft.stt.Recognizer = mock.MagicMock
        config = {'stt': {
                 'module': 'kaldi',
                 'kaldi': {'uri': 'https://test.com'},
            },
            "lang": "en-US"
        }
        mock_get.return_value = config

        kaldiResponse = mock.MagicMock()
        kaldiResponse.json.return_value = {
                'hypotheses': [{'utterance': '     [noise]     text'},
                               {'utterance': '     asdf'}]
        }
        mock_post.return_value = kaldiResponse
        audio = mock.MagicMock()
        stt = mycroft.stt.KaldiSTT()
        self.assertEquals(stt.execute(audio), 'text')
