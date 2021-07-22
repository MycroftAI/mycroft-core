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

import time
import mimetypes
import re

from threading import Lock
from mycroft.audio.services import AudioBackend
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG


class GuiPlayerService(AudioBackend):
    def __init__(self, config, bus=None, name='guiplayer'):
        super(GuiPlayerService, self).__init__(config, bus)
        self.config = config
        self.process = None
        self.bus = bus
        self.name = name
        self._is_playing = False
        self._paused = False
        self.tracks = []
        self.index = 0
        self.track_lock = Lock()
        self.track_meta_from_player = None
        self.track_meta_from_cps = None

        self.bus.on('GuiPlayerServicePlay', self._play)
        self.bus.on(
            'gui.player.media.service.sync.status',
            self.track_media_status)
        self.bus.on(
            'gui.player.media.service.get.meta',
            self.sync_meta_from_player)
        self.bus.on('play:status', self.sync_meta_to_player)

    def supported_uris(self):
        return ['file', 'http', 'https']

    def clear_list(self):
        with self.track_lock:
            self.tracks = []

    def add_list(self, tracks):
        with self.track_lock:
            self.tracks += tracks
            LOG.info("Track list is " + str(tracks))

    def _get_track(self, track_data):
        if isinstance(track_data, list):
            track = track_data[0]
            mime = track_data[1]
            mime = mime.split('/')
        else:  # Assume string
            track = track_data
            mime = self.find_mime(track)
        return track, mime

    def _play(self, message):
        """ Handle _play call from play signal. """
        repeat = message.data.get("repeat", False)
        with self.track_lock:
            if len(self.tracks) > self.index:
                track, mime = self._get_track(self.tracks[self.index])
            else:
                return

        # Indicate to audio service which track is being played
        if self._track_start_callback:
            self._track_start_callback(track)

        try:
            if 'video' in mime[0]:
                LOG.debug("Sending Video Type")
                self.bus.emit(Message("playback.display.video.type"))
            else:
                LOG.debug("Sending Audio Type")
                self.bus.emit(Message("playback.display.audio.type"))
        except BaseException:
            LOG.debug("Cannot Determine Mime Type Falling Back To List Check")
            mediatype = self.fallback_type_check(track)
            if mediatype == "video":
                LOG.debug("Falling Back To Video Type")
                self.bus.emit(Message("playback.display.video.type"))
            else:
                LOG.debug("Falling Back To Audio Type")
                self.bus.emit(Message("playback.display.audio.type"))

        time.sleep(0.5)
        self.bus.emit(
            Message(
                "gui.player.media.service.play", {
                    "track": track, "mime": mime, "repeat": repeat}))
        LOG.debug('Player Emitted gui.player.media.service.play')
        self.send_meta_to_player()

    def play(self, repeat=False):
        """ Play media playback. """
        self.index = 0
        self.bus.emit(Message('GuiPlayerServicePlay', {'repeat': repeat}))

    def stop(self):
        """ Stop media playback. """
        if self._is_playing:
            self.bus.emit(Message("gui.player.media.service.stop"))

    def pause(self):
        """ Pause media playback. """
        self.bus.emit(Message("gui.player.media.service.pause"))

    def resume(self):
        """ Resume paused playback. """
        self.bus.emit(Message("gui.player.media.service.resume"))

    def next(self):
        """ Skip to next track in playlist. """
        # Todo
        pass

    def previous(self):
        """ Skip to previous track in playlist. """
        # Todo
        pass

    def lower_volume(self):
        if not self._paused:
            self.pause()  # poor-man's ducking

    def restore_volume(self):
        if not self._paused:
            self.resume()  # poor-man's unducking

    def sync_meta_from_player(self, message):
        """ Gets metadata from QMediaPlayer. """
        self.track_meta_from_player = message.data

    def sync_meta_to_player(self, message):
        """ Gets metadata from CPS Service. """
        self.track_meta_from_cps = message.data

    def send_meta_to_player(self):
        """ Send CPS metadata to QMediaPlayer. """
        if self.track_meta_from_cps:
            self.bus.emit(Message("gui.player.media.service.set.meta",
                                  self.track_meta_from_cps))
        else:
            LOG.debug("CPS Metadata Not Available")

    def track_media_status(self, message):
        """ Track Media Status from QMediaPlayer.
            QMediaPlayer Status Enums:
                0. Stopped
                1. Playing
                2. Paused
        """
        current_state = message.data.get("state")
        if current_state == 1:
            self._is_playing = True
        if current_state == 2:
            self._paused = True
        if current_state == 0:
            self.bus.emit(Message("playback.display.remove"))

    def track_info(self):
        """
            Fetch info about current playing track.
            Returns:
                Dict with track info.
        """
        if self.track_meta_from_player:
            return self.track_meta_from_player
        else:
            pass

    def find_mime(self, path):
        """ Determine mime type. """
        mime = None
        mime = mimetypes.guess_type(path)
        if mime:
            return mime
        else:
            return None

    def fallback_type_check(self, path):
        """ Fallback check for video type in track urls. """
        if "videoplayback" in path:
            return "video"
        else:
            return "audio"


def load_service(base_config, bus):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'guiplayer' and
                backends[b].get('active', True)]
    instances = [GuiPlayerService(s[1], bus, s[0]) for s in services]
    return instances
