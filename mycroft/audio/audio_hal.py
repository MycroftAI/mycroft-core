# Copyright 2022 Mycroft AI Inc.
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
"""Audio hardware abstraction layer.

Used by the audio user interface (AUI) to play sound effects and streams.
"""
import functools
import threading
import typing

import vlc

from mycroft.messagebus import Message
from mycroft.messagebus.client import MessageBusClient


class AudioHAL:
    """Audio hardware abstraction layer"""

    def __init__(
        self, fg_channels: typing.Iterable[str], bg_channels: typing.Iterable[str],
    ):
        self._fg_channels = list(fg_channels)
        self._bg_channels = list(bg_channels)

        self._vlc = None

        # Foreground channels use a standard media player
        self._fg_players = {}

        self._fg_media_ids: typing.Dict[str, typing.Optional[str]] = {}

        # Background channels use a list media player
        self._bg_players = {}

        self._bg_media_ids: typing.Dict[str, typing.Optional[str]] = {}

    def initialize(self, bus: MessageBusClient):
        self.bus = bus

        self._vlc = vlc.Instance("--no-video")

        # Foreground channels use a standard media player
        self._fg_players = {
            channel: self._vlc.media_player_new() for channel in self._fg_channels
        }

        self._fg_media_ids = {}

        self._attach_fg_events()

        # Background channels use a list media player
        self._bg_players = {
            channel: self._vlc.media_list_player_new() for channel in self._bg_channels
        }

        self._bg_media_ids = {}

    def shutdown(self):
        self._vlc = None
        self._fg_players = {}
        self._bg_players = {}

    def _attach_fg_events(self):
        for fg_channel, fg_player in self._fg_players.items():
            event_manager = fg_player.event_manager()
            event_manager.event_attach(
                vlc.EventType.MediaPlayerEndReached,
                functools.partial(self._fg_media_finished, fg_channel),
            )

    def _fg_media_finished(self, channel, _event):
        media_id = self._fg_media_ids.get(channel)

        if media_id is not None:
            self.bus.emit(
                Message(
                    "mycroft.audio.hal.media-finished",
                    data={"channel": channel, "media_id": media_id},
                )
            )

    def _attach_bg_events(self):
        for bg_channel, bg_player in self._bg_players.items():
            event_manager = bg_player.event_manager()
            event_manager.event_attach(
                vlc.EventType.MediaListPlayerPlayed,
                functools.partial(self._bg_media_finished, bg_channel),
            )

    def _bg_media_finished(self, channel, _event):
        media_id = self._bg_media_ids.get(channel)

        if media_id is not None:
            self.bus.emit(
                Message(
                    "mycroft.audio.hal.media-finished",
                    data={"channel": channel, backgroud: True, "media_id": media_id},
                )
            )

    # -------------------------------------------------------------------------

    def play_foreground(
        self, channel: str, uri: str, return_duration: bool = False
    ) -> typing.Optional[int]:
        assert channel in self._fg_players, f"No player for channel: {channel}"
        player = self._fg_players[channel]

        media = self._vlc.media_new(uri)

        duration_ms: typing.Optional[int] = None
        if return_duration:
            # Only parse media for duration on request, since it can block for a
            # long time on URIs.
            media.parse()
            duration_ms = media.get_duration()

        player.set_media(media)
        player.play()

        return duration_ms

    def stop_foreground(self, channel: str):
        assert channel in self._fg_players, f"No player for channel: {channel}"

        player = self._fg_players[channel]
        player.stop()

    # -------------------------------------------------------------------------

    def start_background(self, channel: str, uri_playlist: typing.Iterable[str]):
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]

        # Create new playlist each time
        playlist = self._vlc.media_list_new()
        for uri in uri_playlist:
            media = self._vlc.media_new(uri)
            playlist.add_media(media)

        list_player.set_media_list(playlist)
        list_player.play()

    def stop_background(self, channel: str):
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]
        list_player.stop()

    def pause_background(self, channel: str):
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]
        list_player.pause()

    def resume_background(self, channel: str):
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]
        list_player.play()

    def handle_background_finished(self, channel, _event):
        pass
