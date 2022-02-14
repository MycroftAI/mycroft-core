#!/usr/bin/env python3
import queue
import shlex
import subprocess
import tempfile
import threading
import time
import typing
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from mycroft.configuration import Configuration
from mycroft.messagebus import Message
from mycroft.messagebus.client import MessageBusClient
from mycroft.util import check_for_signal, resolve_resource_file
from mycroft.util.log import LOG

from .audio_hal import AudioHAL


class ForegroundChannel(IntEnum):
    """Available foreground channels (sound effects, TTS)"""

    EFFECT = 0
    SPEECH = 1


# Fixed sample rate for sound effects
EFFECT_SAMPLE_RATE = 48_000  # Hz
EFFECT_CHANNELS = 2


# -----------------------------------------------------------------------------


@dataclass
class TTSRequest:
    """Chunk of TTS audio to play.

    A single sentence or paragraph is typically split into multiple chunks for
    faster time to first audio.

    Chunks belonging to the same original sentence or paragraph share the same
    session id.
    """

    uri: str
    session_id: str
    chunk_index: int
    num_chunks: int
    listen: bool = False

    @property
    def is_first_chunk(self):
        return self.chunk_index <= 0

    @property
    def is_last_chunk(self):
        return self.chunk_index >= (self.num_chunks - 1)


class RepeatingTimer(threading.Thread):
    """Repeatedly calls a function at a fixed interval in a separate thread"""

    def __init__(self, interval: float, function):
        self.interval = interval
        self.function = function
        self.cancelled = False

        super().__init__()

    def cancel(self):
        self.cancelled = True

    def start(self):
        self.cancelled = False
        super().start()

    def run(self):
        seconds_to_wait = self.interval

        while True:
            if self.cancelled:
                break

            time.sleep(seconds_to_wait)

            if self.cancelled:
                break

            start_time = time.time()

            try:
                self.function()
            except Exception:
                LOG.exception("timer")

            end_time = time.time()

            if self.cancelled:
                break

            # Take run time of function into account to avoid drift
            seconds_elapsed = end_time - start_time
            seconds_to_wait = max(0, self.interval - seconds_elapsed)


# -----------------------------------------------------------------------------


class AudioUserInterface:
    """Audio interface between Mycroft and the Audio HAL.

    Listens for relevant bus events and manipulates the audio system.
    """

    def __init__(self):
        self.config = Configuration.get()

        self._ahal = AudioHAL(
            audio_sample_rate=EFFECT_SAMPLE_RATE, audio_channels=EFFECT_CHANNELS
        )

        self._start_listening_uri = "file://" + resolve_resource_file(
            self.config["sounds"]["start_listening"]
        )

        self._acknowledge_uri = "file://" + resolve_resource_file(
            self.config["sounds"]["acknowledge"]
        )

        self._last_skill_id: typing.Optional[str] = None
        self._ignore_session_id: typing.Optional[str] = None

        self._bg_position_timer = RepeatingTimer(1.0, self.send_stream_position)

        self._speech_queue = queue.Queue()
        self._speech_thread: typing.Optional[threading.Thread] = None
        self._tts_session_id: typing.Optional[str] = None
        self._speech_finished = threading.Event()

        self._bus_events = {
            "recognizer_loop:record_begin": self.handle_start_listening,
            "recognizer_loop:audio_output_start": self.handle_tts_started,
            "recognizer_loop:audio_output_end": self.handle_tts_finished,
            # "mycroft.volume.duck": self.handle_duck_volume,
            # "mycroft.volume.unduck": self.handle_unduck_volume,
            "skill.started": self.handle_skill_started,
            "skill.ended": self.handle_skill_ended,
            "mycroft.audio.play-sound": self.handle_play_sound,
            "mycroft.tts.stop": self.handle_tts_stop,
            "mycroft.tts.speak-chunk": self.handle_tts_chunk,
            "mycroft.audio.hal.media-finished": self.handle_media_finished,
            "mycroft.audio.service.play": self.handle_stream_play,
            "mycroft.audio.service.pause": self.handle_stream_pause,
            "mycroft.audio.service.resume": self.handle_stream_resume,
            "mycroft.audio.service.stop": self.handle_stream_stop,
        }

    def initialize(self, bus: MessageBusClient):
        """Initializes the service"""
        self.bus = bus
        self._ahal.initialize(self.bus)

        # TTS queue/thread
        self._speech_queue = queue.Queue()
        self._speech_thread = threading.Thread(target=self._speech_run, daemon=True)
        self._speech_thread.start()

        self._bg_position_timer.start()

        self._attach_events()

    def _attach_events(self):
        """Adds bus event handlers"""
        for event_name, handler in self._bus_events.items():
            self.bus.on(event_name, handler)

        # TODO: Seek events

    def shutdown(self):
        """Shuts down the service"""
        try:
            self._bg_position_timer.cancel()

            self._detach_events()

            # Stop text to speech
            self._drain_speech_queue()

            if self._speech_thread is not None:
                self._speech_queue.put(None)
                self._speech_thread.join()
                self._speech_thread = None

            self._ahal.shutdown()
        except Exception:
            LOG.exception("error shutting down")

    def _detach_events(self):
        """Removes bus event handlers"""
        for event_name, handler in self._bus_events.items():
            self.bus.remove(event_name, handler)

    # -------------------------------------------------------------------------

    def handle_tts_stop(self, _message):
        """Called in response to a 'stop' command"""
        self._ignore_session_id = self._tts_session_id
        self._drain_speech_queue()

        # Stop foreground channels
        self._ahal.stop_foreground(ForegroundChannel.SPEECH)

        if self._tts_session_id is not None:
            self._finish_tts_session(session_id=self._tts_session_id)

        self._last_skill_id = None
        self._tts_session_id = None

    def _duck_volume(self):
        """Lower TTS and background stream volumes during voice commands"""
        self._ahal.stop_foreground(ForegroundChannel.SPEECH)
        self._ahal.set_background_volume(0.3)
        LOG.info("Ducked volume")

    def _unduck_volume(self):
        """Restore volumes after voice commands"""
        self._ahal.set_background_volume(1.0)
        LOG.info("Unducked volume")

    # -------------------------------------------------------------------------

    def handle_play_sound(self, message):
        """Handler for skills' play_sound_uri"""
        uri = message.data.get("uri")
        volume = message.data.get("volume")
        self._play_effect(uri, volume=volume)

    def handle_start_listening(self, _message):
        """Play sound when Mycroft begins recording a command"""

        self._duck_volume()
        self._play_effect(self._start_listening_uri)

    def _play_effect(self, uri: str, volume: typing.Optional[float] = None):
        """Play sound effect from uri"""
        if uri:
            assert uri.startswith("file://"), "Only file URIs are supported for effects"
            file_path = uri[len("file://") :]
            self._ahal.play_foreground(
                ForegroundChannel.EFFECT, file_path, cache=True, volume=volume
            )
            LOG.info("Played sound: %s", uri)

    def handle_skill_started(self, message):
        """Handler for skills' activity_started"""
        skill_id = message.data.get("skill_id")
        if skill_id != self._last_skill_id:
            LOG.info("Clearing TTS queue for skill: %s", skill_id)

            self._drain_speech_queue()

            # Stop TTS speaking
            self._ahal.stop_foreground(ForegroundChannel.SPEECH)

            # Transition to new skill
            self._last_skill_id = skill_id

    def handle_skill_ended(self, message):
        """Handler for skills' activity_ended"""
        self._unduck_volume()

    def _drain_speech_queue(self):
        """Ensures the text to speech queue is emptied"""
        while not self._speech_queue.empty():
            self._speech_queue.get()

    def handle_tts_chunk(self, message):
        """Queues a text to speech audio chunk to be played"""
        uri = message.data["uri"]
        session_id = message.data.get("session_id", "")
        chunk_index = message.data.get("chunk_index", 0)
        num_chunks = message.data.get("num_chunks", 1)
        listen = message.data.get("listen", False)

        if session_id == self._ignore_session_id:
            # Drop chunks from previously stopped session
            LOG.info("Ignoring TTS chunk from session: %s", session_id)
            return

        request = TTSRequest(
            uri=uri,
            session_id=session_id,
            chunk_index=chunk_index,
            num_chunks=num_chunks,
            listen=listen,
        )
        self._speech_queue.put(request)

        LOG.info("Queued TTS chunk %s/%s: %s", chunk_index + 1, num_chunks, uri)

    def handle_tts_started(self, message):
        # Duck music
        self._ahal.set_background_volume(0.3)

    def handle_tts_finished(self, message):
        # Unduck music
        self._ahal.set_background_volume(1.0)

    def handle_media_finished(self, message):
        """Callback when VLC media item has finished playing"""
        channel = message.data.get("channel")
        background = message.data.get("background", False)
        media_id = message.data.get("media_id")

        if channel == ForegroundChannel.SPEECH:
            if media_id == self._tts_session_id:
                # Signal speech thread to play next TTS chunk
                self._speech_finished.set()
        elif background:
            # Signal background stream complete
            LOG.info("Background stream finished")
            self.bus.emit(Message("mycroft.audio.queue_end"))

    def _speech_run(self):
        """Thread proc for text to speech"""
        try:
            while True:
                request = self._speech_queue.get()
                if request is None:
                    break

                self._tts_session_id = request.session_id

                if request.is_first_chunk:
                    self.bus.emit(Message("recognizer_loop:audio_output_start"))

                # TODO: Support other URI types
                assert request.uri.startswith("file://")
                file_path = request.uri[len("file://") :]

                # Play TTS chunk
                self._speech_finished.clear()
                duration_sec = self._ahal.play_foreground(
                    ForegroundChannel.SPEECH, file_path, media_id=request.session_id,
                )

                assert duration_sec is not None
                LOG.info(
                    "Speaking TTS chunk %s/%s for %s sec from session %s",
                    request.chunk_index + 1,
                    request.num_chunks,
                    duration_sec,
                    request.session_id,
                )

                # Wait at most a half a second after audio should have finished.
                #
                # This is done in case VLC fails to inform us that the media
                # item has finished playing.
                timeout = 0.5 + duration_sec
                self._speech_finished.wait(timeout=timeout)

                if request.is_last_chunk:
                    self._finish_tts_session(
                        session_id=request.session_id, listen=request.listen
                    )

        except Exception:
            LOG.exception("error is speech thread")

    def _finish_tts_session(self, session_id: str, listen: bool = False):
        # Report speaking finished for speak(wait=True)
        self.bus.emit(
            Message("mycroft.tts.speaking-finished", data={"session_id": session_id},)
        )

        self.bus.emit(Message("recognizer_loop:audio_output_end"))
        if listen:
            self.bus.emit(Message("mycroft.mic.listen"))

        # This check will clear the "signal"
        check_for_signal("isSpeaking")

        LOG.info("TTS session finished: %s", session_id)

    # -------------------------------------------------------------------------

    def handle_stream_play(self, message):
        """Handler for mycroft.audio.service.play

        Play tracks using the background stream.
        """
        tracks = message.data.get("tracks", [])
        if not tracks:
            LOG.warning("Play message received with not tracks: %s", message.data)
            return

        uri_playlist = []
        for track in tracks:
            if isinstance(track, str):
                # URI
                uri_playlist.append(track)
            else:
                # (URI, mimetype)
                uri = next(iter(track))
                uri_playlist.append(uri)

        # Stop previous stream
        self._ahal.stop_background()

        LOG.info("Playing background stream: %s", uri_playlist)
        self._ahal.start_background(uri_playlist)

    def handle_stream_pause(self, _message):
        """Handler for mycroft.audio.service.pause"""
        LOG.debug("Pausing background stream")
        self._ahal.pause_background()

    def handle_stream_resume(self, _message):
        """Handler for mycroft.audio.service.resume"""
        LOG.debug("Resuming background stream")
        self._ahal.resume_background()

    def handle_stream_stop(self, _message):
        """Handler for mycroft.audio.service.stop"""
        # Don't ever actually stop the background stream.
        # This lets us resume it later at any point.
        self._ahal.pause_background()

    def send_stream_position(self):
        """Sends out background stream position to skills"""
        if not self._ahal.is_background_playing():
            return

        position_ms = self._ahal.get_background_time()
        if position_ms >= 0:
            self.bus.emit(
                Message(
                    "mycroft.audio.service.position", data={"position_ms": position_ms}
                )
            )
