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
import ctypes
import os
import signal
import subprocess
import tempfile
import typing
from pathlib import Path

import numpy as np
import sdl2
import sdl2.sdlmixer as mixer

from mycroft.messagebus import Message
from mycroft.messagebus.client import MessageBusClient
from mycroft.util.log import LOG

ChannelType = int
HookMusicFunc = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int
)


class AudioHAL:
    """Audio hardware abstraction layer.

    Provides access to the audio output device through VLC.
    Output "channels" are categorized as:

    * Foreground
      * Transient sounds effects or speech from text to speech
    * Background
      * Long-running audio stream

    Each channel may only have one media item at a time.
    """

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate

        # Cache of mixer chunks
        self._fg_cache: typing.Dict[ChannelType, mixer.Mix_Chunk] = {}

        # Mixer chunks to free after finished playing
        self._fg_free: typing.Dict[ChannelType, mixer.Mix_Chunk] = {}

        # Media ids by channel
        self._fg_media_ids: typing.Dict[ChannelType, typing.Optional[str]] = {}
        self._bg_media_id: typing.Optional[str] = None

        # Background VLC process
        self._bg_proc: typing.Optional[subprocess.Popen] = None
        self._bg_paused: bool = False
        self._bg_volume: float = 1.0
        self._bg_position: int = 0

        # Callback must be defined inline in order to capture "self"
        @ctypes.CFUNCTYPE(None, ctypes.c_int)
        def fg_channel_finished(channel):
            """Callback when foreground media item is finished playing"""
            try:
                media_id = self._fg_media_ids.get(channel)

                if media_id is not None:
                    self.bus.emit(
                        Message(
                            "mycroft.audio.hal.media-finished",
                            data={"channel": channel, "media_id": media_id},
                        )
                    )

                chunk = self._fg_free.get(channel)
                if chunk is not None:
                    mixer.Mix_FreeChunk(chunk)
            except Exception:
                LOG.exception("Error finishing channel: %s", channel)

        self._fg_channel_finished = fg_channel_finished

        # Callback must be defined inline in order to capture "self"
        @ctypes.CFUNCTYPE(None)
        def bg_finished():
            """Callback when background media item is finished playing"""
            try:
                media_id = self._bg_media_id

                if media_id is not None:
                    self.bus.emit(
                        Message(
                            "mycroft.audio.hal.media-finished",
                            data={"background": True, "media_id": media_id},
                        )
                    )
            except Exception:
                LOG.exception("Error finishing music")

        self._bg_finished = bg_finished

        @HookMusicFunc
        def bg_music_hook(udata, stream, length):
            if self._bg_paused or (self._bg_proc is None):
                # Write silence
                ctypes.memset(stream, 0, length)
            else:
                if self._bg_proc.poll() is not None:
                    # Stream finished
                    self.stop_background()
                    self._bg_finished()
                else:
                    # Music data
                    data = self._bg_proc.stdout.read(length)

                    if 0 <= self._bg_volume < 1:
                        array = np.frombuffer(data, dtype=np.int16) * self._bg_volume
                        data = array.astype(np.int16).tobytes()

                    # ctypes.memset(stream, data, length)
                    for i in range(len(data)):
                        stream[i] = data[i]

                    self._bg_position += length

        self._bg_music_hook = bg_music_hook

        self._bg_playlist_file = tempfile.NamedTemporaryFile(suffix=".m3u", mode="w+")

    def initialize(self, bus: MessageBusClient):
        self.bus = bus

        LOG.debug("Initializing SDL mixer")

        # TODO: Parameterize
        ret = mixer.Mix_OpenAudio(48000, sdl2.AUDIO_S16SYS, 2, 2048)
        assert ret >= 0, mixer.Mix_GetError().decode("utf8")

        # TODO: Init MP3, FLAC, etc

        mixer.Mix_ChannelFinished(self._fg_channel_finished)
        # mixer.Mix_HookMusicFinished(self._bg_finished)

        # mixer.Mix_SetMusicCMD("vlc -I dummy --no-video --no-repeat".encode())

        self._reset_caches()

    def shutdown(self):
        self._reset_caches()

        self.stop_background()

        mixer.Mix_CloseAudio()

    def _reset_caches(self):
        self._fg_free = {}
        self._fg_cache = {}
        self._fg_media_ids = {}
        self._bg_media_id = None

    def _stop_bg_process(self):
        if self._bg_proc is not None:
            if self._bg_proc.poll() is None:
                self._bg_proc.terminate()
                try:
                    self._bg_proc.communicate(timeout=0.5)
                except subprocess.TimeoutExpired:
                    self._bg_proc.kill()

            self._bg_proc = None

    def _bg_media_finished(self, channel, _event):
        """Callback when background playlist is finished playing"""
        media_id = self._bg_media_ids.get(channel)

        if media_id is not None:
            self.bus.emit(
                Message(
                    "mycroft.audio.hal.media-finished",
                    data={"channel": channel, "background": True, "media_id": media_id},
                )
            )

    # -------------------------------------------------------------------------

    def play_foreground(
        self,
        channel: ChannelType,
        file_path: typing.Union[str, Path],
        media_id: typing.Optional[str] = None,
        volume: typing.Optional[float] = None,
        cache: bool = False,
    ) -> float:
        """Play an audio file on a foreground channel."""
        file_path_str = str(file_path)
        chunk: typing.Optional[mixer.Mix_Chunk] = None

        if cache:
            chunk = self._fg_cache.get(file_path_str)

        if chunk is None:
            chunk = mixer.Mix_LoadWAV(file_path_str.encode())
            assert chunk, mixer.Mix_GetError().decode("utf8")

            if cache:
                self._fg_cache[file_path_str] = chunk

        duration_sec = chunk.contents.alen / (48000 * 2)
        self._fg_media_ids[channel] = media_id

        self._fg_free[channel] = chunk if not cache else None

        if volume is not None:
            mixer.Mix_Volume(channel, self._clamp_volume(volume))

        mixer.Mix_PlayChannel(channel, chunk, 0)

        return duration_sec

    def stop_foreground(self, channel: int = -1):
        """Stop media on a foreground channel (-1 for all)"""
        mixer.Mix_HaltChannel(channel)

    def set_foreground_volume(self, volume: float, channel: int = -1):
        """Set volume [0-1] of a foreground channel (-1 for all)"""
        mixer.Mix_Volume(channel, self._clamp_volume(volume))

    def _clamp_volume(volume: float) -> int:
        volume_num = int(volume * mixer.MIX_MAX_VOLUME)
        volume_num = max(0, volume_num)
        volume_num = min(mixer.MIX_MAX_VOLUME, volume_num)

        return volume_num

    # -------------------------------------------------------------------------

    def start_background(self, uri_playlist: typing.Iterable[str]):
        """Start a playlist playing on a background channel"""
        self._stop_bg_process()

        self._bg_playlist_file.truncate(0)

        for item in uri_playlist:
            print(item, file=self._bg_playlist_file)

        print("vlc://quit", file=self._bg_playlist_file)
        self._bg_playlist_file.seek(0)

        self._bg_proc = subprocess.Popen(
            [
                "vlc",
                "-I",
                "dummy",
                "--no-video",
                "--sout",
                f"#transcode{{acodec=s16l,samplerate={self.sample_rate},channels=2}}:std{{access=file,mux=wav,dst=-}}",
                self._bg_playlist_file.name,
            ],
            stdout=subprocess.PIPE,
        )

        self._bg_position = 0
        self._bg_paused = False
        mixer.Mix_HookMusic(self._bg_music_hook, None)

        LOG.info("Playing background music")

    def stop_background(self):
        """Stop the background channel"""
        mixer.Mix_HookMusic(HookMusicFunc(), None)
        self._stop_bg_process()
        self._bg_position = 0

    def pause_background(self):
        """Pause the background channel"""
        self._bg_paused = True

        if self._bg_proc is not None:
            # Pause process
            os.kill(self._bg_proc.pid, signal.SIGSTOP)

    def resume_background(self):
        """Resume the background channel"""
        if self._bg_proc is not None:
            # Resume process
            os.kill(self._bg_proc.pid, signal.SIGCONT)

        self._bg_paused = False

    def set_background_volume(self, volume: float):
        self._bg_volume = max(0, min(volume, 1))

    def get_background_time(self) -> int:
        """Get position of background stream in milliseconds"""
        # Assume 48Khz, 16-bit stereo
        bytes_per_ms = (48_000 * 2 * 2) // 1000

        return self._bg_position // bytes_per_ms
