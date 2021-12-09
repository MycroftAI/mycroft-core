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
    """Handle "speak" message

    Parse sentences and invoke text to speech service.
    """
    config = Configuration.get()
    Configuration.set_config_update_handlers(bus)
    global _last_stop_signal

    # if the message is targeted and audio is not the target don't
    # don't synthezise speech
    event.context = event.context or {}
    if event.context.get('destination') and not \
            ('debug_cli' in event.context['destination'] or
             'audio' in event.context['destination']):
        return

    # Get conversation ID
    if event.context and 'ident' in event.context:
        ident = event.context['ident']
    else:
        ident = 'unknown'

    start = time.time()  # Time of speech request
    with lock:
        stopwatch = Stopwatch()
        stopwatch.start()
        utterance = event.data['utterance']
        listen = event.data.get('expect_response', False)
        # This is a bit of a hack for Picroft.  The analog audio on a Pi blocks
        # for 30 seconds fairly often, so we don't want to break on periods
        # (decreasing the chance of encountering the block).  But we will
        # keep the split for non-Picroft installs since it give user feedback
        # faster on longer phrases.
        #
        # TODO: Remove or make an option?  This is really a hack, anyway,
        # so we likely will want to get rid of this when not running on Mimic
        if (config.get('enclosure', {}).get('platform') != "picroft" and
                len(re.findall('<[^>]*>', utterance)) == 0):
            # Remove any whitespace present after the period,
            # if a character (only alpha) ends with a period
            # ex: A. Lincoln -> A.Lincoln
            # so that we don't split at the period
            utterance = re.sub(r'\b([A-za-z][\.])(\s+)', r'\g<1>', utterance)
            chunks = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\;|\?)\s',
                              utterance)
            # Apply the listen flag to the last chunk, set the rest to False
            chunks = [(chunks[i], listen if i == len(chunks) - 1 else False)
                      for i in range(len(chunks))]
            for chunk, listen in chunks:
                # Check if somthing has aborted the speech
                if (_last_stop_signal > start or
                        check_for_signal('buttonPress')):
                    # Clear any newly queued speech
                    tts.playback.clear()
                    break
                try:
                    mute_and_speak(chunk, ident, listen)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    LOG.error('Error in mute_and_speak', exc_info=True)
        else:
            mute_and_speak(utterance, ident, listen)

        stopwatch.stop()
    report_timing(ident, 'speech', stopwatch, {'utterance': utterance,
                                               'tts': tts.__class__.__name__})


def mute_and_speak(utterance, ident, listen=False):
    """Mute mic and start speaking the utterance using selected tts backend.

    Args:
        utterance:  The sentence to be spoken
        ident:      Ident tying the utterance to the source query
    """
    global tts_hash
    # update TTS object if configuration has changed
    if tts_hash != hash(str(config.get('tts', ''))):
        global tts
        # Stop tts playback thread
        tts.playback.stop()
        tts.playback.join()
        # Create new tts instance
        tts = TTSFactory.create()
        tts.init(bus)
        tts_hash = hash(str(config.get('tts', '')))

    LOG.info("Speak: " + utterance)
    try:
        tts.execute(utterance, ident, listen)
    except RemoteTTSException as e:
        LOG.error(e)
        mimic_fallback_tts(utterance, ident, listen)
    except Exception:
        LOG.exception('TTS execution failed.')


def _get_mimic_fallback():
    """Lazily initializes the fallback TTS if needed."""
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
    bus.on('mycroft.stop', handle_stop)
    bus.on('mycroft.audio.speech.stop', handle_stop)
    bus.on('speak', handle_speak)

    tts = TTSFactory.create()
    tts.init(bus)
    tts_hash = hash(str(config.get('tts', '')))


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
