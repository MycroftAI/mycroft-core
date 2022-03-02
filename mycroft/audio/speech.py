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
import os
import re
import time
import typing
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from mycroft.configuration import Configuration
from mycroft.metrics import report_timing, Stopwatch
from mycroft.tts import TTSFactory
from mycroft.util import check_for_signal, create_signal, resolve_resource_file
from mycroft.util.log import LOG
from mycroft.messagebus.message import Message
from mycroft.tts.remote_tts import RemoteTTSException
from mycroft.tts.mimic_tts import Mimic


@dataclass
class TTSSession:
    id: str
    cache_paths: typing.List[typing.Union[str, Path]] = field(default_factory=list)
    expire_after: typing.Optional[datetime] = None


bus = None  # Mycroft messagebus connection
config = None
tts = None
tts_hash = None
lock = Lock()
mimic_fallback_obj = None
tts_session_cache: typing.Dict[str, TTSSession] = dict()

_last_stop_signal = 0


def handle_speak(event):
    """Handle "speak" message

    Parse sentences and invoke text to speech service.
    """
    config = Configuration.get()
    Configuration.set_config_update_handlers(bus)
    global _last_stop_signal

    # if the message is targeted and audio is not the target don't
    # don't synthezise speech
    event.context = event.context or {}
    if event.context.get("destination") and not (
        "debug_cli" in event.context["destination"]
        or "audio" in event.context["destination"]
    ):
        return

    # Get conversation ID
    if event.context and "ident" in event.context:
        ident = event.context["ident"]
    else:
        ident = "unknown"

    start = time.time()  # Time of speech request
    with lock:
        stopwatch = Stopwatch()
        stopwatch.start()
        utterance = event.data["utterance"]
        cache_only = event.data.get("cache_only", False)
        speak = not cache_only
        listen = event.data.get("expect_response", False)

        cache_key = event.data.get("cache_key")
        if cache_key and speak:
            cache_keep = event.data.get("cache_keep", False)
            was_in_cache = _speak_from_cache(cache_key, keep=cache_keep, listen=listen)
            if was_in_cache:
                # Successfully spoken from cache
                return

        tts_session_id = cache_key or str(uuid4())
        if cache_only:
            # Create new TTS session
            expire_after: typing.Optional[datetime] = None
            expire_after_str = event.data.get("cache_expire")
            if expire_after_str:
                expire_after = datetime.fromisoformat(expire_after_str)

            tts_session_cache[tts_session_id] = TTSSession(
                id=tts_session_id, expire_after=expire_after
            )

        create_signal("isSpeaking")

        # This is a bit of a hack for Picroft.  The analog audio on a Pi blocks
        # for 30 seconds fairly often, so we don't want to break on periods
        # (decreasing the chance of encountering the block).  But we will
        # keep the split for non-Picroft installs since it give user feedback
        # faster on longer phrases.
        #
        # TODO: Remove or make an option?  This is really a hack, anyway,
        # so we likely will want to get rid of this when not running on Mimic
        if (
            config.get("enclosure", {}).get("platform") != "picroft"
            and len(re.findall("<[^>]*>", utterance)) == 0
        ):
            # Remove any whitespace present after the period,
            # if a character (only alpha) ends with a period
            # ex: A. Lincoln -> A.Lincoln
            # so that we don't split at the period
            # NOTE: This does not work because things like "a.m." and "I.P."
            # will have their whitespace removed too.
            #
            # utterance = re.sub(r'\b([A-za-z][\.])(\s+)', r'\g<1>', utterance)

            chunks = re.split(
                r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\;|\?)\s", utterance
            )
            # Apply the listen flag to the last chunk, set the rest to False
            chunks = [
                (chunks[i], listen if i == len(chunks) - 1 else False)
                for i in range(len(chunks))
            ]
            num_chunks = len(chunks)

            for chunk_idx, (chunk, listen) in enumerate(chunks):
                # Check if somthing has aborted the speech
                if _last_stop_signal > start or check_for_signal("buttonPress"):
                    # Clear any newly queued speech
                    tts.playback.clear()
                    break
                try:
                    mute_and_speak(
                        chunk,
                        ident,
                        listen,
                        session_id=tts_session_id,
                        chunk_idx=chunk_idx,
                        num_chunks=num_chunks,
                        speak=speak,
                    )
                except KeyboardInterrupt:
                    raise
                except Exception:
                    LOG.error("Error in mute_and_speak", exc_info=True)

            if cache_only:
                bus.emit(event.reply("speak.cache.reply", {"key": tts_session_id}))
        else:
            mute_and_speak(utterance, ident, listen)

        stopwatch.stop()
    report_timing(
        ident,
        "speech",
        stopwatch,
        {"utterance": utterance, "tts": tts.__class__.__name__},
    )


def mute_and_speak(
    utterance,
    ident,
    listen=False,
    session_id=None,
    chunk_idx=0,
    num_chunks=1,
    speak=True,
):
    """Mute mic and start speaking the utterance using selected tts backend.

    Args:
        utterance:  The sentence to be spoken
        ident:      Ident tying the utterance to the source query
    """
    global tts_hash
    # update TTS object if configuration has changed
    if tts_hash != hash(str(config.get("tts", ""))):
        global tts
        # Stop tts playback thread
        tts.playback.stop()
        tts.playback.join()
        # Create new tts instance
        tts = TTSFactory.create()
        tts.init(bus)
        tts_hash = hash(str(config.get("tts", "")))

    LOG.debug("Listen=%s, Speak:%s" % (listen, utterance))
    try:
        cached_path = tts.execute(
            utterance,
            ident,
            listen,
            session_id=session_id,
            chunk_idx=chunk_idx,
            num_chunks=num_chunks,
            speak=speak,
        )

        if not speak:
            session = tts_session_cache[session_id]
            session.cache_paths.append(cached_path)

            if session.expire_after:
                LOG.info(
                    "Cached utterance for session %s until %s",
                    session_id,
                    session.expire_after,
                )
            else:
                LOG.info("Cached utterance for session %s", session_id)
    except RemoteTTSException as e:
        LOG.error(e)
        mimic_fallback_tts(utterance, ident, listen)
    except Exception:
        LOG.exception("TTS execution failed.")


def _get_mimic_fallback():
    """Lazily initializes the fallback TTS if needed."""
    global mimic_fallback_obj
    if not mimic_fallback_obj:
        config = Configuration.get()
        tts_config = config.get("tts", {}).get("mimic", {})
        lang = config.get("lang", "en-us")
        tts = Mimic(lang, tts_config)
        tts.validator.validate()
        tts.init(bus)
        mimic_fallback_obj = tts

    return mimic_fallback_obj


def mimic_fallback_tts(utterance, ident, listen):
    """Speak utterance using fallback TTS if connection is lost.

    Args:
        utterance (str): sentence to speak
        ident (str): interaction id for metrics
        listen (bool): True if interaction should end with mycroft listening
    """
    tts = _get_mimic_fallback()
    LOG.debug("Mimic fallback, utterance : " + str(utterance))
    tts.execute(utterance, ident, listen)


def handle_stop(event):
    """Handle stop message.

    Shutdown any speech.
    """
    global _last_stop_signal
    if check_for_signal("isSpeaking", -1):
        _last_stop_signal = time.time()
        tts.playback.clear()  # Clear here to get instant stop
        bus.emit(Message("mycroft.stop.handled", {"by": "TTS"}))


def handle_pause(event):
    tts.playback.pause()


def handle_resume(event):
    tts.playback.resume()


def _speak_from_cache(key: str, keep: bool = False, listen: bool = False) -> bool:
    if keep:
        session = tts_session_cache.get(key)
    else:
        session = tts_session_cache.pop(key, None)

    if session is None:
        LOG.warning("No TTS session cache for %s", key)
        return False

    if (session.expire_after is not None) and (datetime.now() > session.expire_after):
        LOG.debug("TTS session expired for %s", key)

        # Ensure session is gone
        tts_session_cache.pop(key, None)

        return False

    # Verify that all paths exist
    for cache_path in session.cache_paths:
        if not os.path.exists(cache_path):
            return False

    create_signal("isSpeaking")

    num_chunks = len(session.cache_paths)
    for chunk_idx, cache_path in enumerate(session.cache_paths):
        audio_uri = "file://" + str(cache_path)
        bus.emit(
            Message(
                "mycroft.tts.speak-chunk",
                data={
                    "uri": audio_uri,
                    "session_id": key,
                    "chunk_index": chunk_idx,
                    "num_chunks": num_chunks,
                    "listen": listen if chunk_idx == (num_chunks - 1) else False,
                },
            )
        )

    return True


def init(messagebus):
    """Start speech related handlers.

    Args:
        messagebus: Connection to the Mycroft messagebus
    """

    global bus
    global tts
    global tts_hash
    global config

    bus = messagebus
    Configuration.set_config_update_handlers(bus)
    config = Configuration.get()

    tts = TTSFactory.create()
    tts.init(bus)
    tts_hash = hash(str(config.get("tts", "")))

    bus.on("mycroft.stop", handle_stop)
    bus.on("mycroft.audio.speech.stop", handle_stop)
    bus.on("mycroft.audio.speech.pause", handle_pause)
    bus.on("mycroft.audio.speech.resume", handle_resume)
    bus.on("speak", handle_speak)
    bus.on("speak.cache", handle_speak)


def shutdown():
    """Shutdown the audio service cleanly.

    Stop any playing audio and make sure threads are joined correctly.
    """
    if tts:
        tts.playback.stop()
        tts.playback.join()
    if mimic_fallback_obj:
        mimic_fallback_obj.playback.stop()
        mimic_fallback_obj.playback.join()
