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
import shlex
import subprocess
import threading
import typing
from pathlib import Path

import vlc

from mycroft.messagebus import Message
from mycroft.messagebus.client import MessageBusClient
from mycroft.util.log import LOG

Channel = str
MediaId = str

EFFECT_ARG = "%1"


class AudioHAL:
    """Audio hardware abstraction layer.

    Provides access to the audio output device through VLC.
    Output "channels" are categorized as:

    * Effect (1 channel)
      * Short, transient sounds effects
    * Foreground (any number of channels)
      * Medium-length audio, such as text to speech
    * Background (any number of channels)
      * Long-running audio streams (playlists)

    Each channel may only have one media item or playlist at a time.
    """

    def __init__(
        self,
        foreground_channels: typing.Iterable[Channel],
        background_channels: typing.Iterable[Channel],
        effect_command: typing.Optional[typing.Union[str, typing.Iterable[str]]] = None,
    ):
        self._fg_channels = list(foreground_channels)
        self._bg_channels = list(background_channels)

        # Default to aplay
        self.effect_command: typing.List[str] = ["aplay", EFFECT_ARG]

        if isinstance(effect_command, str):
            # Split command
            self.effect_command = shlex.split(effect_command)
        elif effect_command is not None:
            # Command + args
            self.effect_command = list(effect_command)

        # Foreground/background channels use VLC
        self._vlc: typing.Optional[vlc.Instance] = None

        # Foreground channels use a standard media player
        self._fg_players = {}

        # User-supplied id of media playing on each foreground channel
        self._fg_media_ids: typing.Dict[Channel, typing.Optional[MediaId]] = {}

        # Background channels use a list media player
        self._bg_players = {}

        # User-supplied id of media playing on each background channel
        self._bg_media_ids: typing.Dict[Channel, typing.Optional[MediaId]] = {}

    def initialize(self, bus: MessageBusClient):
        """Create VLC object and channel media players"""
        self.bus = bus

        # Create VLC objects
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

        self._attach_bg_events()

    def _attach_fg_events(self):
        """Listen for 'end reached' events in foreground media players"""
        for fg_channel, fg_player in self._fg_players.items():
            event_manager = fg_player.event_manager()
            event_manager.event_attach(
                vlc.EventType.MediaPlayerEndReached,
                functools.partial(self._fg_media_finished, fg_channel),
            )

    # NOTE: Cannot include type hints here because of vlc
    def _fg_media_finished(self, channel, _event):
        """Callback when foreground media item is finished playing"""
        media_id = self._fg_media_ids.pop(channel, "")
        self.bus.emit(
            Message(
                "mycroft.audio.hal.media-finished",
                data={"channel": channel, "background": False, "media_id": media_id},
            )
        )

    def _attach_bg_events(self):
        """Listen for 'player played' events in background media players"""
        for bg_channel, bg_player in self._bg_players.items():
            event_manager = bg_player.event_manager()
            event_manager.event_attach(
                vlc.EventType.MediaListPlayerPlayed,
                functools.partial(self._bg_media_finished, bg_channel),
            )

    # NOTE: Cannot include type hints here because of vlc
    def _bg_media_finished(self, channel, _event):
        """Callback when background playlist is finished playing"""
        media_id = self._bg_media_ids.pop(channel, "")
        self.bus.emit(
            Message(
                "mycroft.audio.hal.media-finished",
                data={"channel": channel, "background": True, "media_id": media_id},
            )
        )

    def shutdown(self):
        """Delete VLC object and media players"""
        for player in self._fg_players.values():
            player.release()

        self._fg_players = {}

        for list_player in self._bg_players.values():
            list_player.release()

        self._bg_players = {}

        if self._vlc is not None:
            self._vlc.release()
            self._vlc = None

    # -------------------------------------------------------------------------
    # Effects
    # -------------------------------------------------------------------------

    def play_effect(self, wav_path: typing.Union[str, Path]):
        """Plays a WAV sound effect from a file path"""

        # Replace effect arg with path to WAV
        command = [e if e != EFFECT_ARG else str(wav_path) for e in self.effect_command]
        subprocess.run(command, check=False)

    # -------------------------------------------------------------------------
    # Foreground
    # -------------------------------------------------------------------------

    def play_foreground(
        self,
        channel: Channel,
        uri: str,
        media_id: typing.Optional[MediaId] = None,
        return_duration: bool = False,
    ) -> typing.Optional[int]:
        """Play a URI on a foreground channel.

        Returns:
            duration of media item in milliseconds if return_duration = True
        """
        assert channel in self._fg_players, f"No player for channel: {channel}"
        player = self._fg_players[channel]

        media = self._vlc.media_new(uri)

        duration_ms: typing.Optional[int] = None
        if return_duration:
            # Only parse media for duration on request, since it can block for a
            # long time on URIs.
            media.parse()
            duration_ms = media.get_duration()

        player.stop()
        player.set_media(media)

        self._fg_media_ids[channel] = media_id
        player.play()

        return duration_ms

    def stop_foreground(self, channel: Channel):
        """Stop media on a foreground channel"""
        assert channel in self._fg_players, f"No player for channel: {channel}"

        player = self._fg_players[channel]
        player.stop()
        self._fg_media_ids.pop(channel, None)

    def set_foreground_volume(self, channel: Channel, volume: int):
        """Set volume of a foreground channel"""
        assert channel in self._fg_players, f"No player for channel: {channel}"
        player = self._fg_players[channel]
        player.audio_set_volume(volume)

    # -------------------------------------------------------------------------
    # Background
    # -------------------------------------------------------------------------

    def start_background(
        self,
        channel: Channel,
        uri_playlist: typing.Iterable[str],
        media_id: typing.Optional[MediaId] = None,
    ):
        """Start a playlist playing on a background channel"""
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]

        # Create new playlist each time
        playlist = self._vlc.media_list_new()
        for uri in uri_playlist:
            media = self._vlc.media_new(uri)
            playlist.add_media(media)

        list_player.stop()
        list_player.set_media_list(playlist)

        self._bg_media_ids[channel] = media_id
        list_player.play()

    def stop_background(self, channel: Channel):
        """Stop the playlist on a background channel"""
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]
        list_player.stop()

    def pause_background(self, channel: Channel):
        """Pause the playlist on a background channel"""
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]
        player = list_player.get_media_player()

        if player.is_playing():
            player.pause()

    def resume_background(self, channel: str):
        """Resume the playlist on a background channel"""
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]
        player = list_player.get_media_player()

        if not player.is_playing():
            player.play()

    def set_background_volume(self, channel: Channel, volume: int):
        """Set volume for a background channel"""
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]
        list_player.get_media_player().audio_set_volume(volume)

    def get_background_time(self, channel: Channel) -> int:
        """Get media time in milliseconds for a background channel"""
        assert channel in self._bg_players, f"No player for channel: {channel}"
        list_player = self._bg_players[channel]
        return list_player.get_media_player().get_time()
