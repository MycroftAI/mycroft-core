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

from unittest.mock import MagicMock, patch

import mycroft.stt
from mycroft.configuration import Configuration

from test.util import base_config


class TestSTT(unittest.TestCase):
    @patch.object(Configuration, 'get')
    def test_factory(self, mock_get):
        mycroft.stt.STTApi = MagicMock()
        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'mycroft',
                    'wit': {'credential': {'token': 'FOOBAR'}},
                    'google': {'credential': {'token': 'FOOBAR'}},
                    'bing': {'credential': {'token': 'FOOBAR'}},
                    'houndify': {'credential': {'client_id': 'FOO',
                                                "client_key": 'BAR'}},
                    'google_cloud': {
                        'credential': {
                            'json': {}
                        }
                    },
                    'ibm': {
                        'credential': {
                            'token': 'FOOBAR'
                        },
                        'url': 'https://test.com/'
                    },
                    'kaldi': {'uri': 'https://test.com'},
                    'mycroft': {'uri': 'https://test.com'}
                },
                'lang': 'en-US'
            })
        mock_get.return_value = config

        stt = mycroft.stt.STTFactory.create()
        self.assertEqual(type(stt), mycroft.stt.MycroftSTT)

        config['stt']['module'] = 'google'
        stt = mycroft.stt.STTFactory.create()
        self.assertEqual(type(stt), mycroft.stt.GoogleSTT)

        config['stt']['module'] = 'google_cloud'
        stt = mycroft.stt.STTFactory.create()
        self.assertEqual(type(stt), mycroft.stt.GoogleCloudSTT)

        config['stt']['module'] = 'ibm'
        stt = mycroft.stt.STTFactory.create()
        self.assertEqual(type(stt), mycroft.stt.IBMSTT)

        config['stt']['module'] = 'kaldi'
        stt = mycroft.stt.STTFactory.create()
        self.assertEqual(type(stt), mycroft.stt.KaldiSTT)

        config['stt']['module'] = 'wit'
        stt = mycroft.stt.STTFactory.create()
        self.assertEqual(type(stt), mycroft.stt.WITSTT)

    @patch.object(Configuration, 'get')
    def test_stt(self, mock_get):
        mycroft.stt.STTApi = MagicMock()
        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'mycroft',
                    'mycroft': {'uri': 'https://test.com'}
                },
                'lang': 'en-US'
            })
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

    @patch.object(Configuration, 'get')
    def test_mycroft_stt(self, mock_get):
        mycroft.stt.STTApi = MagicMock()
        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'mycroft',
                    'mycroft': {'uri': 'https://test.com'}
                },
                'lang': 'en-US'
            })
        mock_get.return_value = config

        stt = mycroft.stt.MycroftSTT()
        audio = MagicMock()
        stt.execute(audio, 'en-us')
        self.assertTrue(mycroft.stt.STTApi.called)

    @patch.object(Configuration, 'get')
    def test_google_stt(self, mock_get):
        mycroft.stt.Recognizer = MagicMock
        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'google',
                    'google': {'credential': {'token': 'FOOBAR'}},
                },
                'lang': 'en-US'
            })
        mock_get.return_value = config

        audio = MagicMock()
        stt = mycroft.stt.GoogleSTT()
        stt.execute(audio)
        self.assertTrue(stt.recognizer.recognize_google.called)

    @patch.object(Configuration, 'get')
    def test_google_cloud_stt(self, mock_get):
        mycroft.stt.Recognizer = MagicMock
        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'google_cloud',
                    'google_cloud': {
                        'credential': {
                            'json': {}
                        }
                    },
                },
                'lang': 'en-US'
            })
        mock_get.return_value = config

        audio = MagicMock()
        stt = mycroft.stt.GoogleCloudSTT()
        stt.execute(audio)
        self.assertTrue(stt.recognizer.recognize_google_cloud.called)

    @patch('mycroft.stt.post')
    @patch.object(Configuration, 'get')
    def test_ibm_stt(self, mock_get, mock_post):
        import json

        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'ibm',
                    'ibm': {
                        'credential': {
                            'token': 'FOOBAR'
                        },
                        'url': 'https://test.com'
                    },
                },
                'lang': 'en-US'
            }
        )
        mock_get.return_value = config

        requests_object = MagicMock()
        requests_object.status_code = 200
        requests_object.text = json.dumps({
            'results': [
                {
                    'alternatives': [
                        {
                            'confidence': 0.96,
                            'transcript': 'sample response'
                        }
                    ],
                    'final': True
                }
            ],
            'result_index': 0
        })
        mock_post.return_value = requests_object

        audio = MagicMock()
        audio.sample_rate = 16000

        stt = mycroft.stt.IBMSTT()
        stt.execute(audio)

        test_url_base = 'https://test.com/v1/recognize'
        mock_post.assert_called_with(test_url_base,
                                     auth=('apikey', 'FOOBAR'),
                                     headers={
                                         'Content-Type': 'audio/x-flac',
                                         'X-Watson-Learning-Opt-Out': 'true'
                                     },
                                     data=audio.get_flac_data(),
                                     params={
                                         'model': 'en-US_BroadbandModel',
                                         'profanity_filter': 'false'
                                     })

    @patch.object(Configuration, 'get')
    def test_wit_stt(self, mock_get):
        mycroft.stt.Recognizer = MagicMock
        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'wit',
                    'wit': {'credential': {'token': 'FOOBAR'}},
                },
                'lang': 'en-US'
            })
        mock_get.return_value = config

        audio = MagicMock()
        stt = mycroft.stt.WITSTT()
        stt.execute(audio)
        self.assertTrue(stt.recognizer.recognize_wit.called)

    @patch('mycroft.stt.post')
    @patch.object(Configuration, 'get')
    def test_kaldi_stt(self, mock_get, mock_post):
        mycroft.stt.Recognizer = MagicMock
        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'kaldi',
                    'kaldi': {'uri': 'https://test.com'},
                },
                'lang': 'en-US'
            })
        mock_get.return_value = config

        kaldiResponse = MagicMock()
        kaldiResponse.json.return_value = {
                'hypotheses': [{'utterance': '     [noise]     text'},
                               {'utterance': '     asdf'}]
        }
        mock_post.return_value = kaldiResponse
        audio = MagicMock()
        stt = mycroft.stt.KaldiSTT()
        self.assertEqual(stt.execute(audio), 'text')

    @patch.object(Configuration, 'get')
    def test_bing_stt(self, mock_get):
        mycroft.stt.Recognizer = MagicMock
        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'bing',
                    'bing': {'credential': {'token': 'FOOBAR'}},
                },
                'lang': 'en-US'
            })
        mock_get.return_value = config

        audio = MagicMock()
        stt = mycroft.stt.BingSTT()
        stt.execute(audio)
        self.assertTrue(stt.recognizer.recognize_bing.called)

    @patch.object(Configuration, 'get')
    def test_houndify_stt(self, mock_get):
        mycroft.stt.Recognizer = MagicMock
        config = base_config()
        config.merge(
            {
                'stt': {
                    'module': 'houndify',
                    'houndify': {'credential': {
                        'client_id': 'FOO',
                        'client_key': "BAR"}}
                },
                'lang': 'en-US'
            })
        mock_get.return_value = config

        audio = MagicMock()
        stt = mycroft.stt.HoundifySTT()
        stt.execute(audio)
        self.assertTrue(stt.recognizer.recognize_houndify.called)
