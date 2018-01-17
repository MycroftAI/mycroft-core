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
from abc import ABCMeta, abstractmethod


class AudioBackend():
    """
        Base class for all audio backend implementations.

        Args:
            config: configuration dict for the instance
            emitter: eventemitter or websocket object
    """
    __metaclass__ = ABCMeta

    def __init__(self, config, emitter):
        self._track_start_callback = None

    @abstractmethod
    def supported_uris(self):
        """
            Returns: list of supported uri types.
        """
        pass

    @abstractmethod
    def clear_list(self):
        """
            Clear playlist
        """
        pass

    @abstractmethod
    def add_list(self, tracks):
        """
            Add tracks to backend's playlist.

            Args:
                tracks: list of tracks.
        """
        pass

    @abstractmethod
    def play(self):
        """
            Start playback.
        """
        pass

    @abstractmethod
    def stop(self):
        """
            Stop playback.
        """
        pass

    def set_track_start_callback(self, callback_func):
        """
            Register callback on track start, should be called as each track
            in a playlist is started.
        """
        self._track_start_callback = callback_func

    def pause(self):
        """
            Pause playback.
        """
        pass

    def resume(self):
        """
            Resume paused playback.
        """
        pass

    def next(self):
        """
            Skip to next track in playlist.
        """
        pass

    def previous(self):
        """
            Skip to previous track in playlist.
        """
        pass

    def lower_volume(self):
        """
            Lower volume.
        """
        pass

    def restore_volume(self):
        """
            Restore normal volume.
        """
        pass

    def track_info(self):
        """
            Fetch info about current playing track.

            Returns:
                Dict with track info.
        """
        ret = {}
        ret['artist'] = ''
        ret['album'] = ''
        return ret
