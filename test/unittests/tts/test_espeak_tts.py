import unittest
from unittest import mock

from mycroft.tts.espeak_tts import ESpeak


@mock.patch('mycroft.tts.tts.PlaybackThread')
class TestMimic(unittest.TestCase):
    @mock.patch('mycroft.tts.espeak_tts.subprocess')
    def test_get_tts(self, mock_subprocess, _):
        conf = {
            "lang": "english-us",
            "voice": "m1"
        }
        e = ESpeak('en-US', conf)
        sentence = 'hello'
        wav_filename = 'abc.wav'
        wav, phonemes = e.get_tts(sentence, wav_filename)
        self.assertTrue(phonemes is None)
        mock_subprocess.call.called_with(['espeak', '-v',
                                          conf['lang'] + '+' + conf['voice'],
                                          '-w', wav_filename,
                                          sentence])
