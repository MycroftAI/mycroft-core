#!/usr/bin/env python3
import queue
import threading
import typing
from collections import deque
from dataclasses import dataclass
from enum import Enum

from mycroft.configuration import Configuration
from mycroft.messagebus import Message
from mycroft.messagebus.client import MessageBusClient
from mycroft.util import check_for_signal, resolve_resource_file
from mycroft.util.log import LOG

from .audio_hal import AudioHAL


class ForegroundChannel(str, Enum):
    SOUND = "sound"
    SPEECH = "speech"


class BackgroundChannel(str, Enum):
    STREAM = "stream"


class Sounds(str, Enum):
    START_LISTENING = "start_listening"
    ACKNOWLEDGE = "acknowledge"


DEFAULT_FOREGROUND = [channel.value for channel in ForegroundChannel]
DEFAULT_BACKGROUND = [channel.value for channel in BackgroundChannel]


@dataclass
class TTSRequest:
    uri: str
    session_id: str
    is_last_chunk: bool = True


class AudioUserInterface:
    def __init__(self, bus: MessageBusClient):
        self.bus = bus
        self.config = Configuration.get()
        self.lock = threading.Lock()

        self._ahal = AudioHAL(
            bus, fg_channels=DEFAULT_FOREGROUND, bg_channels=DEFAULT_BACKGROUND
        )

        self._start_listening_uri = "file://" + resolve_resource_file(
            self.config["sounds"]["start_listening"]
        )

        self._acknowledge_uri = "file://" + resolve_resource_file(
            self.config["sounds"]["acknowledge"]
        )

        self._last_skill_id: typing.Optional[str] = None
        # self._tts_session_id: typing.Optional[str] = None

        self._speech_queue = queue.Queue()
        self._speech_thread: typing.Optional[threading.Thead] = None
        self._speech_finished = threading.Event()

    def initialize(self):
        """Initializes the service"""
        self._speech_queue = queue.Queue()
        self._speech_thread = threading.Thread(target=self._speech_run, daemon=True)
        self._speech_thread.start()

        self._attach_events()

    def _attach_events(self):
        """Adds bus event handlers"""
        self.bus.on("recognizer_loop:wakeword", self.handle_start_listening)

        self.bus.on("skill.started", self.handle_skill_started)
        self.bus.on("mycroft.tts.speak-chunk", self.handle_tts_chunk)

        self.bus.on("mycroft.audio.hal.media-finished", self.handle_media_finished)

        self.bus.on("mycroft.audio.service.play", self.handle_play)
        self.bus.on("mycroft.audio.service.pause", self.handle_pause)
        self.bus.on("mycroft.audio.service.resume", self.handle_resume)
        self.bus.on("mycroft.audio.service.stop", self.handle_stop)

        # TODO: Handle mycroft.stop

        # TODO: Seek events

    def shutdown(self):
        """Shuts down the service"""
        try:
            self._detach_events()

            # Stop text to speech
            self._drain_speech_queue()

            if self._speech_thread is not None:
                self._speech_queue.put(None)
                self._speech_thread.join()
                self._speech_thread = None
        except Exception:
            pass

    def _detach_events(self):
        """Removes bus event handlers"""
        self.bus.remove("recognizer_loop:wakeword", self.handle_start_listening)

        self.bus.remove("skill.started", self.handle_skill_started)
        self.bus.remove("mycroft.tts.speak-chunk", self.handle_tts_chunk)

        self.bus.remove("mycroft.audio.hal.media-finished", self.handle_media_finished)

        self.bus.remove("mycroft.audio.service.play", self.handle_play)
        self.bus.remove("mycroft.audio.service.pause", self.handle_pause)
        self.bus.remove("mycroft.audio.service.resume", self.handle_resume)
        self.bus.remove("mycroft.audio.service.stop", self.handle_stop)

    # -------------------------------------------------------------------------

    def handle_start_listening(self, _message=None):
        """Play sound when Mycroft is awoken"""
        self._ahal.play_foreground(ForegroundChannel.SOUND, self._start_listening_uri)

    def handle_skill_started(self, message):
        """Play sound when a skill activity begins"""
        self._ahal.play_foreground(ForegroundChannel.SOUND, self._acknowledge_uri)

        skill_id = message.data.get("skill_id")
        if skill_id != self._last_skill_id:
            self._drain_speech_queue()

            # Stop TTS speaking
            self._ahal.stop_foreground(ForegroundChannel.SPEECH)

            # Transition to new skill
            self._last_skill_id = skill_id

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

        # The mycroft.tts.speaking-finished event is sent after the last chunk
        # is played.
        is_last_chunk = chunk_index >= (num_chunks - 1)

        request = TTSRequest(
            uri=uri, session_id=session_id, is_last_chunk=is_last_chunk
        )
        self._speech_queue.put(request)

    def handle_media_finished(self, message):
        channel = message.data.get("channel")
        if channel == ForegroundChannel.SPEECH:
            # Signal speech thread to play next TTS chunk
            self._speech_finished.set()

    def _speech_run(self):
        try:
            while True:
                request = self._speech_queue.get()
                if request is None:
                    break

                self._speech_finished.clear()
                duration_ms = self._ahal.play_foreground(
                    ForegroundChannel.SPEECH, request.uri, return_duration=True
                )

                assert duration is not None

                # Wait at most a second after audio should have finished
                timeout = 1 + (duration_ms / 1000)
                self._speech_finished.wait(timeout=timeout)

                if request.is_last_chunk:
                    # Report speaking finished
                    self.bus.emit(
                        "mycroft.tts.speaking-finished",
                        data={"session_id": request.session_id},
                    )

                    # This check will clear the "signal"
                    check_for_signal("isSpeaking")

        except Exception:
            LOG.exception("error is speech thread")

    # -------------------------------------------------------------------------

    def handle_play(self, message):
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

        LOG.info("Playing %s", uri_playlist)
        self._ahal.start_background(BackgroundChannel.STREAM, uri_playlist=uri_playlist)

    def handle_pause(self, _message):
        LOG.debug("Pausing background")
        self._ahal.pause_background(BackgroundChannel.STREAM)

    def handle_resume(self, _message):
        LOG.debug("Resuming background")
        self._ahal.resume_background(BackgroundChannel.STREAM)

    def handle_stop(self, _message):
        LOG.info("Stopping background")
        self._ahal.stop_background(BackgroundChannel.STREAM)
