import unittest
from unittest import mock

from mycroft.tts.google_tts import GoogleTTS, GoogleTTSValidator
import mycroft.tts.google_tts as google_tts_mod


@mock.patch('mycroft.tts.google_tts.gTTS')
@mock.patch('mycroft.tts.tts.PlaybackThread')
class TestGoogleTTS(unittest.TestCase):
    def test_get_tts(self, _, gtts_mock):
        gtts_response = mock.Mock()
        gtts_mock.return_value = gtts_response
        tts = GoogleTTS('en-US', {})
        sentence = 'help me Obi-Wan Kenobi, you are my only hope'
        mp3_file, vis = tts.get_tts(sentence, 'output.mp3')
        gtts_mock.assert_called_with(text=sentence, lang='en-us')
        gtts_response.save.assert_called_with('output.mp3')

    def test_validator(self, _, gtts_mock):
        validator = GoogleTTSValidator(GoogleTTS('en-US', {}))
        validator.validate_connection()
        with self.assertRaises(Exception):
            def sideeffect(**kwargs):
                raise Exception
            gtts_mock.side_effect = sideeffect
            validator.validate_connection()

    @mock.patch('mycroft.tts.google_tts.tts_langs')
    def test_lang_connection_error(self, mock_get_langs, _, gtts_mock):
        google_tts_mod._supported_langs = None

        def sideeffect(**kwargs):
            raise Exception
        mock_get_langs.side_effect = sideeffect
        tts = GoogleTTS('en-US', {})
        self.assertEqual(tts.google_lang, 'en-us')
