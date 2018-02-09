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
import time

from mycroft.audio.services import AudioBackend
from mycroft.util.log import LOG


class VlcService(AudioBackend):
    def __init__(self, config, emitter=None, name='vlc'):
        super(VlcService, self).__init__(config, emitter)
        self.instance = vlc.Instance()
        self.list_player = self.instance.media_list_player_new()
        self.player = self.instance.media_player_new()
        self.list_player.set_media_player(self.player)
        self.track_list = self.instance.media_list_new()
        self.list_player.set_media_list(self.track_list)
        self.vlc_events = self.player.event_manager()
        self.vlc_events.event_attach(vlc.EventType.MediaPlayerPlaying,
                                     self.track_start, 1)
        self.config = config
        self.emitter = emitter
        self.name = name
        self.normal_volume = None

    def track_start(self, data, other):
        if self._track_start_callback:
            self._track_start_callback(self.track_info()['name'])

    def supported_uris(self):
        return ['file', 'http', 'https']

    def clear_list(self):
        self.track_list = self.instance.media_list_new()
        self.list_player.set_media_list(self.track_list)

    def add_list(self, tracks):
        LOG.info("Track list is " + str(tracks))
        for t in tracks:
            self.track_list.add_media(self.instance.media_new(t))

    def play(self):
        LOG.info('VLCService Play')
        self.list_player.play()

    def stop(self):
        LOG.info('VLCService Stop')
        self.clear_list()
        self.list_player.stop()

    def pause(self):
        self.player.set_pause(1)

    def resume(self):
        self.player.set_pause(0)

    def next(self):
        self.list_player.next()

    def previous(self):
        self.list_player.previous()

    def lower_volume(self):
        if self.normal_volume is None:
            self.normal_volume = self.player.audio_get_volume()
            self.player.audio_set_volume(self.normal_volume / 5)

    def restore_volume(self):
        if self.normal_volume:
            self.player.audio_set_volume(self.normal_volume)
            self.normal_volume = None

    def track_info(self):
        ret = {}
        meta = vlc.Meta
        t = self.player.get_media()
        ret['album'] = t.get_meta(meta.Album)
        ret['artists'] = [t.get_meta(meta.Artist)]
        ret['name'] = t.get_meta(meta.Title)
        return ret


def load_service(base_config, emitter):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'vlc']
    instances = [VlcService(s[1], emitter, s[0]) for s in services]
    return instances
