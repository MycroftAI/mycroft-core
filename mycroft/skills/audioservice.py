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
from os.path import abspath

from mycroft.messagebus.message import Message


def ensure_uri(s):
    """
        Interprete paths as file:// uri's

        Args:
            s: string to be checked

        Returns:
            if s is uri, s is returned otherwise file:// is prepended
    """
    if isinstance(s, str):
        if '://' not in s:
            return 'file://' + abspath(s)
        else:
            return s
    elif isinstance(s, (tuple, list)):
        if '://' not in s[0]:
            return 'file://' + abspath(s[0]), s[1]
        else:
            return s
    else:
        raise ValueError('Invalid track')


class AudioService:
    """
        AudioService class for interacting with the audio subsystem

        Arguments:
            bus: Mycroft messagebus connection
    """

    def __init__(self, bus):
        self.bus = bus
        self.bus.on('mycroft.audio.service.track_info_reply',
                    self._track_info)
        self.info = None

    def _track_info(self, message=None):
        """
            Handler for catching returning track info
        """
        self.info = message.data

    def queue(self, tracks=None):
        """ Queue up a track to playing playlist.

            Args:
                tracks: track uri or list of track uri's
        """
        tracks = tracks or []
        if isinstance(tracks, str):
            tracks = [tracks]
        elif not isinstance(tracks, list):
            raise ValueError
        tracks = [ensure_uri(t) for t in tracks]
        self.bus.emit(Message('mycroft.audio.service.queue',
                              data={'tracks': tracks}))

    def play(self, tracks=None, utterance=None, repeat=None):
        """ Start playback.

            Args:
                tracks: track uri or list of track uri's
                        Each track can be added as a tuple with (uri, mime)
                        to give a hint of the mime type to the system
                utterance: forward utterance for further processing by the
                           audio service.
                repeat: if the playback should be looped
        """
        repeat = repeat or False
        tracks = tracks or []
        utterance = utterance or ''
        if isinstance(tracks, (str, tuple)):
            tracks = [tracks]
        elif not isinstance(tracks, list):
            raise ValueError
        tracks = [ensure_uri(t) for t in tracks]
        self.bus.emit(Message('mycroft.audio.service.play',
                              data={'tracks': tracks,
                                    'utterance': utterance,
                                    'repeat': repeat}))

    def stop(self):
        """ Stop the track. """
        self.bus.emit(Message('mycroft.audio.service.stop'))

    def next(self):
        """ Change to next track. """
        self.bus.emit(Message('mycroft.audio.service.next'))

    def prev(self):
        """ Change to previous track. """
        self.bus.emit(Message('mycroft.audio.service.prev'))

    def pause(self):
        """ Pause playback. """
        self.bus.emit(Message('mycroft.audio.service.pause'))

    def resume(self):
        """ Resume paused playback. """
        self.bus.emit(Message('mycroft.audio.service.resume'))

    def seek(self, seconds=1):
        """
        seek X seconds

         Args:
                seconds (int): number of seconds to seek, if negative rewind
        """
        if seconds < 0:
            self.seek_backward(abs(seconds))
        else:
            self.seek_forward(seconds)

    def seek_forward(self, seconds=1):
        """
        skip ahead X seconds

         Args:
                seconds (int): number of seconds to skip
        """
        self.bus.emit(Message('mycroft.audio.service.seek_forward',
                              {"seconds": seconds}))

    def seek_backward(self, seconds=1):
        """
        rewind X seconds

         Args:
                seconds (int): number of seconds to rewind
        """
        self.bus.emit(Message('mycroft.audio.service.seek_backward',
                              {"seconds": seconds}))

    def track_info(self):
        """ Request information of current playing track.

            Returns:
                Dict with track info.
        """
        self.info = None
        self.bus.emit(Message('mycroft.audio.service.track_info'))
        wait = 5.0
        while self.info is None and wait >= 0:
            time.sleep(0.1)
            wait -= 0.1

        return self.info or {}

    @property
    def is_playing(self):
        return self.track_info() != {}
