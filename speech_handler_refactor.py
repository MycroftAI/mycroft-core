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
import re
import time
from threading import Lock

from mycroft.configuration import Configuration
from mycroft.metrics import report_timing, Stopwatch
from mycroft.tts import TTSFactory
from mycroft.util import check_for_signal
from mycroft.util.log import LOG
from mycroft.messagebus.message import Message
from mycroft.tts.remote_tts import RemoteTTSException
from mycroft.tts.mimic_tts import Mimic

bus = None  # Mycroft messagebus connection
config = None
tts = None
tts_hash = None
lock = Lock()
mimic_fallback_obj = None

_last_stop_signal = 0


def handle_speak(event):
    """Handle 'speak' message by parsing sentences and invoking TTS."""
    global _last_stop_signal
    initialize_config()

    if should_skip_speech(event):
        return

    ident = get_conversation_id(event)
    start = time.time()

    with lock:
        utterance = event.data['utterance']
        listen = event.data.get('expect_response', False)
        chunks = prepare_chunks(utterance, listen)

        for chunk, listen in chunks:
            if should_abort_speech(start):
                clear_speech_queue()
                break
            try:
                mute_and_speak(chunk, ident, listen)
            except KeyboardInterrupt:
                raise
            except Exception:
                LOG.error('Error in mute_and_speak', exc_info=True)

    report_speech_timing(ident, utterance)


def initialize_config():
    """Initialize configuration settings."""
    global config
    config = Configuration.get()
    Configuration.set_config_update_handlers(bus)


def should_skip_speech(event):
    """Determine if the speech synthesis should be skipped."""
    event.context = event.context or {}
    return event.context.get('destination') and not (
        'debug_cli' in event.context['destination'] or
        'audio' in event.context['destination']
    )


def get_conversation_id(event):
    """Extract the conversation ID from the event."""
    return event.context.get('ident', 'unknown')


def prepare_chunks(utterance, listen):
    """Prepare chunks of the utterance for TTS processing."""
    if should_split_utterance(utterance):
        chunks = tts.preprocess_utterance(utterance)
        return [(chunks[i], listen if i == len(chunks) - 1 else False) 
                for i in range(len(chunks))]
    return [(utterance, listen)]


def should_split_utterance(utterance):
    """Determine if the utterance should be split into chunks."""
    return (config.get('enclosure', {}).get('platform') != "picroft" and
            len(re.findall('<[^>]*>', utterance)) == 0)


def should_abort_speech(start):
    """Check if speech should be aborted due to stop signal."""
    return (_last_stop_signal > start or check_for_signal('buttonPress'))


def clear_speech_queue():
    """Clear the TTS speech queue."""
    tts.playback.clear()


def report_speech_timing(ident, utterance):
    """Report the timing of the speech process."""
    stopwatch = Stopwatch()
    stopwatch.start()
    stopwatch.stop()
    report_timing(ident, 'speech', stopwatch, {'utterance': utterance,
                                               'tts': tts.__class__.__name__})


def mute_and_speak(utterance, ident, listen=False):
    """Mute mic and start speaking the utterance using the selected TTS backend."""
    update_tts_if_needed()
    LOG.info("Speak: " + utterance)

    try:
        tts.execute(utterance, ident, listen)
    except RemoteTTSException as e:
        LOG.error(e)
        mimic_fallback_tts(utterance, ident, listen)
    except Exception:
        LOG.exception('TTS execution failed.')


def update_tts_if_needed():
    """Update the TTS object if the configuration has changed."""
    global tts_hash, tts
    new_tts_hash = hash(str(config.get('tts', '')))
    if tts_hash != new_tts_hash:
        if tts:
            tts.playback.detach_tts(tts)
        tts = TTSFactory.create()
        tts.init(bus)
        tts_hash = new_tts_hash


def _get_mimic_fallback():
    """Lazily initialize the fallback TTS if needed."""
    global mimic_fallback_obj
    if not mimic_fallback_obj:
        config = Configuration.get()
        tts_config = config.get('tts', {}).get("mimic", {})
        lang = config.get("lang", "en-us")
        tts = Mimic(lang, tts_config)
        tts.validator.validate()
        tts.init(bus)
        mimic_fallback_obj = tts

    return mimic_fallback_obj


def mimic_fallback_tts(utterance, ident, listen):
    """Speak utterance using fallback TTS if connection is lost."""
    tts = _get_mimic_fallback()
    LOG.debug("Mimic fallback, utterance : " + str(utterance))
    tts.execute(utterance, ident, listen)


def handle_stop(event):
    """Handle stop message and shutdown any speech."""
    global _last_stop_signal
    if check_for_signal("isSpeaking", -1):
        _last_stop_signal = time.time()
        tts.playback.clear()  # Clear here to get instant stop
        bus.emit(Message("mycroft.stop.handled", {"by": "TTS"}))


def init(messagebus):
    """Start speech-related handlers."""
    global bus, tts, tts_hash, config
    bus = messagebus
    initialize_config()
    bus.on('mycroft.stop', handle_stop)
    bus.on('mycroft.audio.speech.stop', handle_stop)
    bus.on('speak', handle_speak)

    tts = TTSFactory.create()
    tts.init(bus)
    tts_hash = hash(str(config.get('tts', '')))


def shutdown():
    """Shutdown the audio service cleanly."""
    if tts:
        tts.playback.stop()
        tts.playback.join()
    if mimic_fallback_obj:
        mimic_fallback_obj.playback.stop()
        mimic_fallback_obj.playback.join()
