from unittest import TestCase, mock

from test.util import Anything
from mycroft.util import (play_ogg, play_mp3, play_wav, play_audio_file,
                          record)

test_config = {
    'play_wav_cmdline': 'mock_wav %1',
    'play_mp3_cmdline': 'mock_mp3 %1',
    'play_ogg_cmdline': 'mock_ogg %1'
}


@mock.patch('mycroft.configuration.Configuration')
@mock.patch('mycroft.util.audio_utils.subprocess')
class TestPlaySounds(TestCase):
    def test_play_ogg(self, mock_subprocess, mock_conf):
        mock_conf.get.return_value = test_config
        play_ogg('insult.ogg')
        mock_subprocess.Popen.assert_called_once_with(['mock_ogg',
                                                       'insult.ogg'],
                                                      env=Anything())

    @mock.patch('mycroft.util.audio_utils.LOG')
    def test_play_ogg_file_not_found(self, mock_log,
                                     mock_subprocess, mock_conf):
        """Test that simple log is raised when subprocess can't find command.
        """
        def raise_filenotfound(*arg, **kwarg):
            raise FileNotFoundError('TEST FILE NOT FOUND')

        mock_subprocess.Popen.side_effect = raise_filenotfound
        mock_conf.get.return_value = test_config
        self.assertEqual(play_ogg('insult.ogg'), None)
        mock_log.error.called_once_with(Anything())

    @mock.patch('mycroft.util.audio_utils.LOG')
    def test_play_ogg_exception(self, mock_log,
                                mock_subprocess, mock_conf):
        """Test that stack trace is provided when unknown excpetion occurs"""
        def raise_exception(*arg, **kwarg):
            raise Exception

        mock_subprocess.Popen.side_effect = raise_exception
        mock_conf.get.return_value = test_config
        self.assertEqual(play_ogg('insult.ogg'), None)
        mock_log.exception.called_once_with(Anything())

    def test_play_mp3(self, mock_subprocess, mock_conf):
        mock_conf.get.return_value = test_config
        play_mp3('praise.mp3')
        mock_subprocess.Popen.assert_called_once_with(['mock_mp3',
                                                       'praise.mp3'],
                                                      env=Anything())

    @mock.patch('mycroft.util.audio_utils.LOG')
    def test_play_mp3_file_not_found(self, mock_log,
                                     mock_subprocess, mock_conf):
        """Test that simple log is raised when subprocess can't find command.
        """
        def raise_filenotfound(*arg, **kwarg):
            raise FileNotFoundError('TEST FILE NOT FOUND')

        mock_subprocess.Popen.side_effect = raise_filenotfound
        mock_conf.get.return_value = test_config
        self.assertEqual(play_mp3('praise.mp3'), None)
        mock_log.error.called_once_with(Anything())

    @mock.patch('mycroft.util.audio_utils.LOG')
    def test_play_mp3_exception(self, mock_log,
                                mock_subprocess, mock_conf):
        """Test that stack trace is provided when unknown excpetion occurs"""
        def raise_exception(*arg, **kwarg):
            raise Exception

        mock_subprocess.Popen.side_effect = raise_exception
        mock_conf.get.return_value = test_config
        self.assertEqual(play_mp3('praise.mp3'), None)
        mock_log.exception.called_once_with(Anything())

    def test_play_wav(self, mock_subprocess, mock_conf):
        mock_conf.get.return_value = test_config
        play_wav('indifference.wav')
        mock_subprocess.Popen.assert_called_once_with(['mock_wav',
                                                       'indifference.wav'],
                                                      env=Anything())

    @mock.patch('mycroft.util.audio_utils.LOG')
    def test_play_wav_file_not_found(self, mock_log,
                                     mock_subprocess, mock_conf):
        """Test that simple log is raised when subprocess can't find command.
        """
        def raise_filenotfound(*arg, **kwarg):
            raise FileNotFoundError('TEST FILE NOT FOUND')

        mock_subprocess.Popen.side_effect = raise_filenotfound
        mock_conf.get.return_value = test_config
        self.assertEqual(play_wav('indifference.wav'), None)
        mock_log.error.called_once_with(Anything())

    @mock.patch('mycroft.util.audio_utils.LOG')
    def test_play_wav_exception(self, mock_log,
                                mock_subprocess, mock_conf):
        """Test that stack trace is provided when unknown excpetion occurs"""
        def raise_exception(*arg, **kwarg):
            raise Exception

        mock_subprocess.Popen.side_effect = raise_exception
        mock_conf.get.return_value = test_config
        self.assertEqual(play_wav('indifference.wav'), None)
        mock_log.exception.called_once_with(Anything())

    def test_play_audio_file(self, mock_subprocess, mock_conf):
        mock_conf.get.return_value = test_config
        play_audio_file('indifference.wav')
        mock_subprocess.Popen.assert_called_once_with(['mock_wav',
                                                       'indifference.wav'],
                                                      env=Anything())
        mock_subprocess.Popen.reset_mock()

        play_audio_file('praise.mp3')
        mock_subprocess.Popen.assert_called_once_with(['mock_mp3',
                                                       'praise.mp3'],
                                                      env=Anything())
        mock_subprocess.Popen.reset_mock()
        mock_conf.get.return_value = test_config
        play_audio_file('insult.ogg')
        mock_subprocess.Popen.assert_called_once_with(['mock_ogg',
                                                       'insult.ogg'],
                                                      env=Anything())


@mock.patch('mycroft.util.audio_utils.subprocess')
class TestRecordSounds(TestCase):
    def test_record_with_duration(self, mock_subprocess):
        mock_proc = mock.Mock()(name='mock process')
        mock_subprocess.Popen.return_value = mock_proc
        rate = 16000
        channels = 1
        filename = '/tmp/test.wav'
        duration = 42
        res = record(filename, duration, rate, channels)
        mock_subprocess.Popen.assert_called_once_with(['arecord',
                                                       '-r', str(rate),
                                                       '-c', str(channels),
                                                       '-d', str(duration),
                                                       filename])
        self.assertEqual(res, mock_proc)

    def test_record_without_duration(self, mock_subprocess):
        mock_proc = mock.Mock(name='mock process')
        mock_subprocess.Popen.return_value = mock_proc
        rate = 16000
        channels = 1
        filename = '/tmp/test.wav'
        duration = 0
        res = record(filename, duration, rate, channels)
        mock_subprocess.Popen.assert_called_once_with(['arecord',
                                                       '-r', str(rate),
                                                       '-c', str(channels),
                                                       filename])
        self.assertEqual(res, mock_proc)
