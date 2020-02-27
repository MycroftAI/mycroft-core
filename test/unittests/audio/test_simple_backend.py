import signal
from threading import Thread
import time
import unittest
import unittest.mock as mock

import mycroft.audio.services.simple as simple
from mycroft.messagebus import Message

"""Tests for the simple audio service backend."""

config = {
    'backends': {
        'test_simple': {
            'type': 'simple',
            'active': True
        }
    }
}


class TestSimpleBackend(unittest.TestCase):
    @mock.patch('mycroft.audio.services.simple.Session')
    def test_find_mime(self, mock_session):
        mock_response = mock.MagicMock()
        mock_session_instance = mock.Mock()
        mock_session_instance.head.return_value = mock_response
        mock_session.return_value = mock_session_instance

        # Check local file
        self.assertEqual(simple.find_mime('file:///hello.mp3'),
                         ['audio', 'mpeg'])

        # Check HTTP
        mock_response.status_code = 200
        mock_response.headers.__getitem__.return_value = 'audio/mpeg'
        self.assertEqual(simple.find_mime('http://mysite.se/hello.mp3'),
                         ['audio', 'mpeg'])

        status_code = 300
        mock_response.headers.__getitem__.return_value = ''
        self.assertEqual(simple.find_mime('http://mysite.se/hello.mp3'),
                         ['audio', 'mpeg'])
        self.assertEqual(
                simple.find_mime('http://mysite.se/hello.mp3?world=True'),
                ['audio', 'mpeg'])

        # Check no info found
        self.assertEqual(simple.find_mime('file:///no_extension'),
                         (None, None))

    def test_load_service(self):
        bus = mock.Mock()
        self.assertEqual(len(simple.load_service(config, bus)), 1)

    def test_playlist_methods(self):
        bus = mock.Mock()
        service = simple.SimpleAudioService(config, bus)
        self.assertEqual(service.tracks, [])
        self.assertTrue(isinstance(service.supported_uris(), list))

        service.add_list(['a', 'b', 'c'])
        self.assertEqual(service.tracks, ['a', 'b', 'c'])

        service.clear_list()
        self.assertEqual(service.tracks, [])

    def test_play(self):
        bus = mock.Mock()
        service = simple.SimpleAudioService(config, bus)
        service.play()
        self.assertTrue(bus.emit.called)

    @mock.patch('mycroft.audio.services.simple.play_mp3')
    @mock.patch('mycroft.audio.services.simple.play_ogg')
    @mock.patch('mycroft.audio.services.simple.play_wav')
    def test_play_internals(self, play_wav_mock, play_ogg_mock, play_mp3_mock):
        bus = mock.Mock()
        process_mock = mock.Mock(name='process')

        completed = False

        def wait_for_completion():
            nonlocal completed
            if not completed:
                return None
            else:
                completed = False
                return True

        process_mock.poll.side_effect = wait_for_completion
        play_wav_mock.return_value = process_mock
        play_ogg_mock.return_value = process_mock
        play_mp3_mock.return_value = process_mock

        service = simple.SimpleAudioService(config, bus)
        tracks = ['a.mp3', ['b.ogg', 'audio/ogg'], ['c.wav', 'audio/wav']]
        service.add_list(tracks)
        service.play()

        thread = Thread(target=service._play, args=[Message('plaything')])
        thread.daemon = True
        thread.start()
        time.sleep(0.1)

        play_mp3_mock.assert_called_with('a.mp3')
        completed = True
        time.sleep(1)
        self.assertEqual(service.index, 1)
        thread.join()

        thread = Thread(target=service._play, args=[Message('plaything')])
        thread.daemon = True
        thread.start()
        time.sleep(0.1)
        play_ogg_mock.assert_called_with('b.ogg')

        service.pause()
        process_mock.send_signal.assert_called_with(signal.SIGSTOP)
        self.assertEqual(service._paused, True)
        service.resume()
        self.assertEqual(service._paused, False)
        completed = True
        thread.join()

        thread = Thread(target=service._play, args=[Message('plaything')])
        thread.daemon = True
        thread.start()
        time.sleep(0.2)
        play_wav_mock.assert_called_with('c.wav')

        service.stop()
        thread.join()
