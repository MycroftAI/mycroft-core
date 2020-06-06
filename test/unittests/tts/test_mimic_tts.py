import stat

import unittest
from unittest import mock

from mycroft.tts.mimic_tts import (Mimic, download_subscriber_voices, BIN,
                                   SUBSCRIBER_VOICES)


device_instance_mock = mock.Mock(name='device_api_instance')
device_instance_mock.is_subscriber = False

subscribed_device = mock.Mock(name='subscriber_device')
subscribed_device.is_subscribed = True
subscribed_device.get_subscriber_voice_url.return_value = 'https://trinity'


@mock.patch('mycroft.tts.mimic_tts.DeviceApi')
@mock.patch('mycroft.tts.tts.PlaybackThread')
class TestMimic(unittest.TestCase):
    @mock.patch('mycroft.tts.mimic_tts.subprocess')
    def test_get_tts(self, mock_subprocess, _, mock_device_api):
        mock_device_api.return_value = device_instance_mock
        m = Mimic('en-US', {})
        wav, phonemes = m.get_tts('hello', 'abc.wav')
        mock_subprocess.check_output.assert_called_once_with(
            m.args + ['-o', 'abc.wav', '-t', 'hello'])
        self.assertEqual(phonemes, mock_subprocess.check_output().decode())

    def test_viseme(self, _, mock_device_api):
        mock_device_api.return_value = device_instance_mock
        m = Mimic('en-US', {})
        viseme_string = ('pau:0.206 m:0.287 ah:0.401 ch:0.513 dh:0.578 '
                         'iy:0.699 s:0.835 ey:1.013 m:1.118 w:1.213 ey:1.345 '
                         'dh:1.415 ae:1.491 t:1.539 b:1.616 r:1.671 ih:1.744 '
                         'k:1.819 s:1.923 d:1.978 ow:2.118 n:2.206 t:2.301 '
                         'pau:2.408')

        vis = m.viseme(viseme_string)
        self.assertEqual(vis,
                         [('4', 0.206), ('4', 0.287), ('0', 0.401),
                          ('3', 0.513), ('3', 0.578), ('0', 0.699),
                          ('3', 0.835), ('0', 1.013), ('4', 1.118),
                          ('2', 1.213), ('0', 1.345), ('3', 1.415),
                          ('0', 1.491), ('3', 1.539), ('4', 1.616),
                          ('2', 1.671), ('0', 1.744), ('3', 1.819),
                          ('3', 1.923), ('3', 1.978), ('2', 2.118),
                          ('3', 2.206), ('3', 2.301), ('4', 2.408)])

    @mock.patch('mycroft.tts.mimic_tts.Thread')
    def test_subscriber(self, mock_thread, _, mock_device_api):
        mock_device_api.return_value = subscribed_device

        m = Mimic('en-US', {'voice': 'trinity'})
        mock_thread.assert_called_with(target=download_subscriber_voices,
                                       args=['trinity'])
        self.assertTrue(m.is_subscriber)
        self.assertEqual(m.args, [BIN, '-voice', 'ap', '-psdur', '-ssml'])
        with mock.patch('mycroft.tts.mimic_tts.exists') as mock_exists:
            mock_exists.return_value = True
            self.assertEqual(m.args, [SUBSCRIBER_VOICES['trinity'], '-voice',
                                      'trinity', '-psdur', '-ssml'])

    @mock.patch('mycroft.tts.mimic_tts.sleep')
    @mock.patch('mycroft.tts.mimic_tts.download')
    def test_download(self, mock_download, mock_sleep, _, mock_device_api):
        mock_device_api.return_value = subscribed_device
        dl = mock.Mock()
        dl.done = False

        def sleep_sideeffect(_):
            """After one sleep call the download should be considered done."""
            nonlocal dl
            dl.done = True

        mock_sleep.side_effect = sleep_sideeffect
        mock_download.return_value = dl

        download_subscriber_voices('trinity')
        self.assertEqual(mock_download.call_args[0][:2],
                         ('https://trinity', '/opt/mycroft/voices/mimic_tn'))
        make_executable = mock_download.call_args[0][2]

        # Check that the excutable flag is set to the downloaded file
        with mock.patch('mycroft.tts.mimic_tts.os.chmod') as mock_chmod:
            with mock.patch('mycroft.tts.mimic_tts.os.stat') as mock_stat:
                st_mock = mock.Mock()
                mock_stat.return_value = st_mock
                st_mock.st_mode = 0
                make_executable('/test')
                mock_chmod.assert_called_with('/test', stat.S_IEXEC)
