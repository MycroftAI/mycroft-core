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
import subprocess
from time import sleep

from mycroft.audio.services import AudioBackend
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
from mycroft.util import play_mp3, play_ogg, play_wav
import mimetypes
from requests import Session


def find_mime(path):
    mime = None
    if path.startswith('http'):
        response = Session().head(path, allow_redirects=True)
        if 200 <= response.status_code < 300:
            mime = response.headers['content-type']
    if not mime:
        mime = mimetypes.guess_type(path)[0]

    if mime:
        return mime.split('/')
    else:
        return (None, None)


class SimpleAudioService(AudioBackend):
    """
        Simple Audio backend for both mpg123 and the ogg123 player.
        This one is rather limited and only implements basic usage.
    """

    def __init__(self, config, bus, name='simple'):

        super(SimpleAudioService, self).__init__(config, bus)
        self.config = config
        self.process = None
        self.bus = bus
        self.name = name
        self._stop_signal = False
        self._is_playing = False
        self.tracks = []
        self.index = 0
        self.supports_mime_hints = True
        mimetypes.init()

        self.bus.on('SimpleAudioServicePlay', self._play)

    def supported_uris(self):
        return ['file', 'http']

    def clear_list(self):
        self.tracks = []

    def add_list(self, tracks):
        self.tracks += tracks
        LOG.info("Track list is " + str(tracks))

    def _play(self, message):
        """ Implementation specific async method to handle playback.
            This allows mpg123 service to use the "next method as well
            as basic play/stop.
        """
        LOG.info('SimpleAudioService._play')
        repeat = message.data.get('repeat', False)
        self._is_playing = True
        if isinstance(self.tracks[self.index], list):
            track = self.tracks[self.index][0]
            mime = self.tracks[self.index][1]
            mime = mime.split('/')
        else:  # Assume string
            track = self.tracks[self.index]
            mime = find_mime(track)
        # Indicate to audio service which track is being played
        if self._track_start_callback:
            self._track_start_callback(track)

        # Replace file:// uri's with normal paths
        track = track.replace('file://', '')
        try:
            if 'mpeg' in mime[1]:
                self.process = play_mp3(track)
            elif 'ogg' in mime[1]:
                self.process = play_ogg(track)
            elif 'wav' in mime[1]:
                self.process = play_wav(track)
            else:
                # If no mime info could be determined guess mp3
                self.process = play_mp3(track)
        except FileNotFoundError as e:
            LOG.error('Couldn\'t play audio, {}'.format(repr(e)))
            self.process = None

        # Wait for completion or stop request
        while (self.process and self.process.poll() is None and
                not self._stop_signal):
            sleep(0.25)

        if self._stop_signal:
            self.process.terminate()
            self.process = None
            self._is_playing = False
            return

        self.index += 1
        # if there are more tracks available play next
        if self.index < len(self.tracks) or repeat:
            if self.index >= len(self.tracks):
                self.index = 0
            self.bus.emit(Message('SimpleAudioServicePlay',
                                  {'repeat': repeat}))
        else:
            self._is_playing = False

    def play(self, repeat=False):
        LOG.info('Call SimpleAudioServicePlay')
        self.index = 0
        self.bus.emit(Message('SimpleAudioServicePlay', {'repeat': repeat}))

    def stop(self):
        LOG.info('SimpleAudioServiceStop')
        self._stop_signal = True
        while self._is_playing:
            sleep(0.1)
        self._stop_signal = False

    def pause(self):
        pass

    def resume(self):
        pass

    def next(self):
        # Terminate process to continue to next
        self.process.terminate()

    def previous(self):
        pass

    def lower_volume(self):
        pass

    def restore_volume(self):
        pass


def load_service(base_config, bus):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'simple' and
                backends[b].get('active', True)]
    instances = [SimpleAudioService(s[1], bus, s[0]) for s in services]
    return instances
