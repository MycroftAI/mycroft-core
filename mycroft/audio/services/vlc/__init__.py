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
import vlc

from mycroft.audio.services import AudioBackend
from mycroft.util.log import LOG


class VlcService(AudioBackend):
    def __init__(self, config, bus=None, name='vlc'):
        super(VlcService, self).__init__(config, bus)
        self.instance = vlc.Instance("--no-video")
        self.list_player = self.instance.media_list_player_new()
        self.player = self.instance.media_player_new()
        self.list_player.set_media_player(self.player)
        self.track_list = self.instance.media_list_new()
        self.list_player.set_media_list(self.track_list)
        self.vlc_events = self.player.event_manager()
        self.vlc_list_events = self.list_player.event_manager()
        self.vlc_events.event_attach(vlc.EventType.MediaPlayerPlaying,
                                     self.track_start, 1)
        self.vlc_events.event_attach(vlc.EventType.MediaPlayerTimeChanged,
                                     self.update_playback_time, None)
        self.vlc_list_events.event_attach(vlc.EventType.MediaListPlayerPlayed,
                                          self.queue_ended, 0)
        self.config = config
        self.bus = bus
        self.name = name
        self.normal_volume = None
        self.low_volume = self.config.get('low_volume', 30)
        self._playback_time = 0
        self.player.audio_set_volume(100)

    @property
    def playback_time(self):
        """ in milliseconds """
        return self._playback_time

    def update_playback_time(self, data, other):
        self._playback_time = data.u.new_time

    def track_start(self, data, other):
        if self._track_start_callback:
            self._track_start_callback(self.track_info()['name'])

    def queue_ended(self, data, other):
        LOG.debug('Queue ended')
        if self._track_start_callback:
            self._track_start_callback(None)

    def supported_uris(self):
        return ['file', 'http', 'https']

    def clear_list(self):
        # Create a new media list
        self.track_list = self.instance.media_list_new()
        # Set list as current track list
        self.list_player.set_media_list(self.track_list)

    def add_list(self, tracks):
        LOG.debug("Track list is " + str(tracks))
        for t in tracks:
            if isinstance(t, list):
                t = t[0]
            self.track_list.add_media(self.instance.media_new(t))

    def play(self, repeat=False):
        """ Play playlist using vlc. """
        LOG.debug('VLCService Play')
        if repeat:
            self.list_player.set_playback_mode(vlc.PlaybackMode.loop)
        else:
            self.list_player.set_playback_mode(vlc.PlaybackMode.default)

        self.list_player.play()

    def stop(self):
        """ Stop vlc playback. """
        LOG.info('VLCService Stop')
        if self.player.is_playing():
            # Restore volume if lowered
            self.restore_volume()
            self.clear_list()
            self.list_player.stop()
            return True
        else:
            return False

    def pause(self):
        """ Pause vlc playback. """
        self.player.set_pause(1)

    def resume(self):
        """ Resume paused playback. """
        self.player.set_pause(0)

    def next(self):
        """ Skip to next track in playlist. """
        self.list_player.next()

    def previous(self):
        """ Skip to previous track in playlist. """
        self.list_player.previous()

    def lower_volume(self):
        """ Lower volume (will be called when mycroft is listening
        or speaking.
        """
        # Lower volume if playing, volume isn't already lowered
        # and ducking is enabled
        if (self.normal_volume is None and self.player.is_playing() and
                self.config.get('duck', False)):
            self.normal_volume = self.player.audio_get_volume()
            self.player.audio_set_volume(self.low_volume)

    def restore_volume(self):
        """ Restore volume to previous level. """
        # if vlc has been lowered restore the volume
        if self.normal_volume:
            self.player.audio_set_volume(self.normal_volume)
            self.normal_volume = None

    def track_info(self):
        """ Extract info of current track. """
        ret = {}
        meta = vlc.Meta
        t = self.player.get_media()
        ret['album'] = t.get_meta(meta.Album)
        ret['artists'] = [t.get_meta(meta.Artist)]
        ret['name'] = t.get_meta(meta.Title)
        return ret

    def get_track_length(self):
        """
        getting the duration of the audio in milliseconds
        """
        return self.player.get_length()

    def get_track_position(self):
        """
        get current position in milliseconds
        """
        return self.player.get_time()

    def set_track_position(self, milliseconds):
        """
        go to position in milliseconds

          Args:
                milliseconds (int): number of milliseconds of final position
        """
        self.player.set_time(int(milliseconds))

    def seek_forward(self, seconds=1):
        """
        skip X seconds

          Args:
                seconds (int): number of seconds to seek, if negative rewind
        """
        seconds = seconds * 1000
        new_time = self.player.get_time() + seconds
        duration = self.player.get_length()
        if new_time > duration:
            new_time = duration
        self.player.set_time(new_time)

    def seek_backward(self, seconds=1):
        """
        rewind X seconds

          Args:
                seconds (int): number of seconds to seek, if negative rewind
        """
        seconds = seconds * 1000
        new_time = self.player.get_time() - seconds
        if new_time < 0:
            new_time = 0
        self.player.set_time(new_time)


def load_service(base_config, bus):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'vlc' and
                backends[b].get('active', False)]
    instances = [VlcService(s[1], bus, s[0]) for s in services]
    return instances
