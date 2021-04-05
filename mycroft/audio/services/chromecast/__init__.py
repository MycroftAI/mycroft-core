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
from mimetypes import guess_type
try:
    import pychromecast
except:
    pychromecast = None
from mycroft.audio.services import RemoteAudioBackend
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG


class ChromecastService(RemoteAudioBackend):
    """
        Audio backend for playback on chromecast. Using the default media
        playback controller included in pychromecast.
    """
    def _connect(self, message):
        LOG.info('Trying to connect to chromecast')
        casts = pychromecast.get_chromecasts()
        if self.config is None or 'identifier' not in self.config:
            LOG.error("Chromecast identifier not found!")
            return  # Can't connect since no id is specified
        else:
            identifier = self.config['identifier']
        for c in casts:
            if c.name == identifier:
                self.cast = c
                break
        else:
            LOG.info('Couldn\'t find chromecast ' + identifier)
            self.connection_attempts += 1
            time.sleep(10)
            self.bus.emit(Message('ChromecastServiceConnect'))
            return

    def __init__(self, config, bus, name='chromecast', cast=None):
        super(ChromecastService, self).__init__(config, bus)
        self.connection_attempts = 0
        self.bus = bus
        self.config = config
        self.name = name

        self.tracklist = []

        if cast is not None:
            self.cast = cast
        else:
            self.cast = None
            self.bus.on('ChromecastServiceConnect', self._connect)
            self.bus.emit(Message('ChromecastServiceConnect'))

    def supported_uris(self):
        """ Return supported uris of chromecast. """
        LOG.info("Chromecasts found: " + str(self.cast))
        if self.cast:
            return ['http', 'https']
        else:
            return []

    def clear_list(self):
        """ Clear tracklist. """
        self.tracklist = []

    def add_list(self, tracks):
        """
            Add list of tracks to chromecast playlist.

            Args:
                tracks (list): list media to add to playlist.
        """
        self.tracklist = tracks
        pass

    def play(self, repeat=False):
        """ Start playback.

        TODO: add playlist support and repeat
        """
        self.cast.wait()  # Make sure the device is ready to receive command
        self.cast.quit_app()
        while self.cast.status.status_text != '':
            time.sleep(1)

        track = self.tracklist[0]
        # Report start of playback to audioservice
        if self._track_start_callback:
            self._track_start_callback(track)
        LOG.debug('track: {}, type: {}'.format(track, guess_type(track)[0]))
        mime = guess_type(track)[0] or 'audio/mp3'
        self.cast.wait()  # Make sure the device is ready to receive command
        self.cast.play_media(track, mime)

    def stop(self):
        """ Stop playback and quit app. """
        if self.cast.media_controller.is_playing:
            self.cast.media_controller.stop()
            self.cast.quit_app()
            return True
        else:
            return False

    def pause(self):
        """ Pause current playback. """
        if not self.cast.media_controller.is_paused:
            self.cast.media_controller.pause()

    def resume(self):
        if self.cast.media_controller.is_paused:
            self.cast.media_controller.play()

    def next(self):
        """ Skip current track. (Not implemented) """
        pass

    def previous(self):
        """ Return to previous track. (Not implemented) """
        pass

    def lower_volume(self):
        # self.cast.volume_down()
        pass

    def restore_volume(self):
        # self.cast.volume_up()
        pass

    def track_info(self):
        """ Return info about currently playing track. """
        info = {}
        ret = {}
        ret['name'] = info.get('name', '')
        if 'album' in info:
            ret['artist'] = info['album']['artists'][0]['name']
            ret['album'] = info['album'].get('name', '')
        else:
            ret['artist'] = ''
            ret['album'] = ''
        return ret

    def shutdown(self):
        """ Disconnect from the device. """
        self.cast.disconnect()


def autodetect(config, bus):
    """
        Autodetect chromecasts on the network and create backends for each
    """
    backends = config.get('backends', [])

    if pychromecast is None or len([b for b in backends
            if backends[b]['type'] == 'chromecast' and
               backends[b].get('active', False)]) > 0:
        # TODO allow enabling/disabling by name
        return []

    casts = pychromecast.get_chromecasts(timeout=5, tries=2, retry_wait=2)
    ret = []
    for c in casts:
        LOG.info(c.name + " found.")
        ret.append(ChromecastService(config, bus, c.name.lower(), c))

    return ret
