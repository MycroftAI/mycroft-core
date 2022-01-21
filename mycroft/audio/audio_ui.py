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
    chunk_index: int
    num_chunks: int

    @property
    def is_last_chunk(self):
        return self.chunk_index >= (self.num_chunks - 1)


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

        self._bus_events = {
            "mycroft.stop": self.handle_mycroft_stop,
            "recognizer_loop:wakeword": self.handle_start_listening,
            "skill.started": self.handle_skill_started,
            "mycroft.tts.speak-chunk": self.handle_tts_chunk,
            "mycroft.audio.hal.media-finished": self.handle_media_finished,
            "mycroft.audio.service.play": self.handle_stream_play,
            "mycroft.audio.service.pause": self.handle_stream_pause,
            "mycroft.audio.service.resume": self.handle_stream_resume,
            "mycroft.audio.service.stop": self.handle_stream_stop,
        }

    def initialize(self):
        """Initializes the service"""
        self._speech_queue = queue.Queue()
        self._speech_thread = threading.Thread(target=self._speech_run, daemon=True)
        self._speech_thread.start()

        self._attach_events()

    def _attach_events(self):
        """Adds bus event handlers"""
        for event_name, handler in self._bus_events.items():
            self.bus.on(event_name, handler)

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
            LOG.exception("error shutting down")

    def _detach_events(self):
        """Removes bus event handlers"""
        for event_name, handler in self._bus_events.items():
            self.bus.remove(event_name, handler)

    # -------------------------------------------------------------------------

    def handle_mycroft_stop(self, _message):
        LOG.info("Stopping all audio")
        self._drain_speech_queue()

        self._ahal.stop_foreground(ForegroundChannel.SOUND)
        self._ahal.stop_foreground(ForegroundChannel.SPEECH)

        self._ahal.pause_background(BackgroundChannel.STREAM)

    # -------------------------------------------------------------------------

    def handle_start_listening(self, _message):
        """Play sound when Mycroft is awoken"""
        self._ahal.stop_foreground(ForegroundChannel.SOUND)
        self._ahal.play_foreground(ForegroundChannel.SOUND, self._start_listening_uri)

    def handle_skill_started(self, message):
        """Play sound when a skill activity begins"""
        self._ahal.stop_foreground(ForegroundChannel.SOUND)
        self._ahal.play_foreground(ForegroundChannel.SOUND, self._acknowledge_uri)

        skill_id = message.data.get("skill_id")
        if skill_id != self._last_skill_id:
            LOG.info("Clearing TTS cache for skill: %s", skill_id)

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

        request = TTSRequest(
            uri=uri,
            session_id=session_id,
            chunk_index=chunk_index,
            num_chunks=num_chunks,
        )
        self._speech_queue.put(request)

        LOG.info("Queued TTS chunk %s/%s: %s", chunk_index + 1, num_chunks, uri)

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

                assert duration_ms is not None
                LOG.info(
                    "Speaking TTS chunk %s/%s for %s ms from session %s",
                    request.chunk_index + 1,
                    request.num_chunks,
                    duration_ms,
                    request.session_id,
                )

                # Wait at most a second after audio should have finished
                timeout = 1 + (duration_ms / 1000)
                self._speech_finished.wait(timeout=timeout)

                if request.is_last_chunk:
                    # Report speaking finished
                    self.bus.emit(
                        Message(
                            "mycroft.tts.speaking-finished",
                            data={"session_id": request.session_id},
                        )
                    )

                    # This check will clear the "signal"
                    check_for_signal("isSpeaking")

                    LOG.info("TTS session finished: %s", request.session_id)

        except Exception:
            LOG.exception("error is speech thread")

    # -------------------------------------------------------------------------

    def handle_stream_play(self, message):
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
        self._ahal.stop_background(BackgroundChannel.STREAM)

        LOG.info("Playing background stream: %s", uri_playlist)
        self._ahal.start_background(BackgroundChannel.STREAM, uri_playlist=uri_playlist)

    def handle_stream_pause(self, _message):
        LOG.debug("Pausing background stream")
        self._ahal.pause_background(BackgroundChannel.STREAM)

    def handle_stream_resume(self, _message):
        LOG.debug("Resuming background stream")
        self._ahal.resume_background(BackgroundChannel.STREAM)

    def handle_stream_stop(self, _message):
        LOG.info("Stopping background stream")
        self._ahal.pause_background(BackgroundChannel.STREAM)
