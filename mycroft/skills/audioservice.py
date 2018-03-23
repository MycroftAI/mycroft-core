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
# Python 2+3 compatibility
from past.builtins import basestring


def ensure_uri(s):
    """
        Interprete paths as file:// uri's

        Args:
            s: string to be checked

        Returns:
            if s is uri, s is returned otherwise file:// is prepended
    """
    if '://' not in s:
        return 'file://' + abspath(s)
    else:
        return s


class AudioService(object):
    """
        AudioService object for interacting with the audio subsystem

        Args:
            emitter: eventemitter or websocket object
    """

    def __init__(self, emitter):
        self.emitter = emitter
        self.emitter.on('mycroft.audio.service.track_info_reply',
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
        if isinstance(tracks, basestring):
            tracks = [tracks]
        elif not isinstance(tracks, list):
            raise ValueError
        tracks = [ensure_uri(t) for t in tracks]
        self.emitter.emit(Message('mycroft.audio.service.queue',
                                  data={'tracks': tracks}))

    def play(self, tracks=None, utterance=''):
        """ Start playback.

            Args:
                tracks: track uri or list of track uri's
                utterance: forward utterance for further processing by the
                           audio service.
        """
        tracks = tracks or []
        if isinstance(tracks, basestring):
            tracks = [tracks]
        elif not isinstance(tracks, list):
            raise ValueError
        tracks = [ensure_uri(t) for t in tracks]
        self.emitter.emit(Message('mycroft.audio.service.play',
                                  data={'tracks': tracks,
                                        'utterance': utterance}))

    def stop(self):
        """ Stop the track. """
        self.emitter.emit(Message('mycroft.audio.service.stop'))

    def next(self):
        """ Change to next track. """
        self.emitter.emit(Message('mycroft.audio.service.next'))

    def prev(self):
        """ Change to previous track. """
        self.emitter.emit(Message('mycroft.audio.service.prev'))

    def pause(self):
        """ Pause playback. """
        self.emitter.emit(Message('mycroft.audio.service.pause'))

    def resume(self):
        """ Resume paused playback. """
        self.emitter.emit(Message('mycroft.audio.service.resume'))

    def track_info(self):
        """ Request information of current playing track.

            Returns:
                Dict with track info.
        """
        self.info = None
        self.emitter.emit(Message('mycroft.audio.service.track_info'))
        wait = 5.0
        while self.info is None and wait >= 0:
            time.sleep(0.1)
            wait -= 0.1

        return self.info or {}

    @property
    def is_playing(self):
        return self.track_info() != {}
