import unittest
import unittest.mock as mock

import mycroft.audio.services.vlc as vlc


config = {
    'backends': {
        'test_simple': {
            'type': 'vlc',
            'active': True
        }
    }
}


@mock.patch('mycroft.audio.services.vlc.vlc')
class TestVlcBackend(unittest.TestCase):
    def test_load_service(self, mock_vlc_mod):
        bus = mock.Mock()
        self.assertEqual(len(vlc.load_service(config, bus)), 1)

    def test_playlist_methods(self, mock_vlc_mod):
        bus = mock.Mock()
        service = vlc.VlcService(config, bus)

        self.assertTrue(isinstance(service.supported_uris(), list))

        # Check that the tracks are added to the track_list
        service.add_list(['a.mp3', 'b.ogg', ['c.wav', 'audio/wav']])
        service.track_list.add_media.has_calls(['a.mp3', 'b.ogg', 'c.wav'])

        # Check that clearing replaces the playlist with an empty one
        empty_list = mock.Mock(name='EmptyList')
        service.instance.media_list_new.return_value = empty_list
        service.clear_list()
        self.assertTrue(service.track_list is empty_list)
        service.list_player.set_media_list.assert_called_with(empty_list)

    def test_playback_methods(self, mock_vlc_mod):
        bus = mock.Mock()
        service = vlc.VlcService(config, bus)

        loop_mode = mock.Mock(name='Loop')
        normal_mode = mock.Mock(name='Normal')
        mock_vlc_mod.PlaybackMode.loop = loop_mode
        mock_vlc_mod.PlaybackMode.default = normal_mode
        # Check normal play
        service.play(repeat=False)
        service.list_player.set_playback_mode.assert_called_with(normal_mode)
        service.list_player.set_playback_mode.reset_mock()
        self.assertTrue(service.list_player.play.called)
        service.list_player.play.reset_mock()
        # Check repeat
        service.play(repeat=True)
        service.list_player.set_playback_mode.assert_called_with(loop_mode)
        service.list_player.set_playback_mode.reset_mock()
        self.assertTrue(service.list_player.play.called)
        service.list_player.play.reset_mock()

        # Check pause
        service.pause()
        service.player.set_pause.assert_called_with(1)
        service.player.set_pause.reset_mock()

        # Check resume
        service.resume()
        service.player.set_pause.assert_called_with(0)
        service.player.set_pause.reset_mock()

        # Check stop
        service.player.is_playing.return_value = False
        self.assertFalse(service.stop())
        service.player.is_playing.return_value = True
        self.assertTrue(service.stop())
