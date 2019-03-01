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
from mycroft.util import create_signal, check_for_signal
from mycroft.util.log import LOG
from mycroft.messagebus.message import Message
from mycroft.tts.remote_tts import RemoteTTSTimeoutException
from mycroft.tts.mimic_tts import Mimic

bus = None  # Mycroft messagebus connection
config = None
tts = None
tts_hash = None
lock = Lock()

_last_stop_signal = 0


def _start_listener(message):
    """
        Force Mycroft to start listening (as if 'Hey Mycroft' was spoken)
    """
    create_signal('startListening')


def handle_speak(event):
    """
        Handle "speak" message
    """
    config = Configuration.get()
    Configuration.init(bus)
    global _last_stop_signal

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
        if event.data.get('expect_response', False):
            # When expect_response is requested, the listener will be restarted
            # at the end of the next bit of spoken audio.
            bus.once('recognizer_loop:audio_output_end', _start_listener)

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
            chunks = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s',
                              utterance)
            for chunk in chunks:
                # Check if somthing has aborted the speech
                if (_last_stop_signal > start or
                        check_for_signal('buttonPress')):
                    # Clear any newly queued speech
                    tts.playback.clear()
                    break
                try:
                    mute_and_speak(chunk, ident)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    LOG.error('Error in mute_and_speak', exc_info=True)
        else:
            mute_and_speak(utterance, ident)

        stopwatch.stop()
    report_timing(ident, 'speech', stopwatch, {'utterance': utterance,
                                               'tts': tts.__class__.__name__})


def mute_and_speak(utterance, ident):
    """
        Mute mic and start speaking the utterance using selected tts backend.

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
        tts.execute(utterance, ident)
    except RemoteTTSTimeoutException as e:
        LOG.error(e)
        mimic_fallback_tts(utterance, ident)
    except Exception as e:
        LOG.error('TTS execution failed ({})'.format(repr(e)))


def mimic_fallback_tts(utterance, ident):
    # fallback if connection is lost
    config = Configuration.get()
    tts_config = config.get('tts', {}).get("mimic", {})
    lang = config.get("lang", "en-us")
    tts = Mimic(lang, tts_config)
    tts.init(bus)
    tts.execute(utterance, ident)


def handle_stop(event):
    """
        handle stop message
    """
    global _last_stop_signal
    if check_for_signal("isSpeaking", -1):
        _last_stop_signal = time.time()
        tts.playback.clear()  # Clear here to get instant stop
        bus.emit(Message("mycroft.stop.handled", {"by": "TTS"}))


def init(messagebus):
    """ Start speech related handlers.

    Arguments:
        messagebus: Connection to the Mycroft messagebus
    """

    global bus
    global tts
    global tts_hash
    global config

    bus = messagebus
    Configuration.init(bus)
    config = Configuration.get()
    bus.on('mycroft.stop', handle_stop)
    bus.on('mycroft.audio.speech.stop', handle_stop)
    bus.on('speak', handle_speak)
    bus.on('mycroft.mic.listen', _start_listener)

    tts = TTSFactory.create()
    tts.init(bus)
    tts_hash = config.get('tts')


def shutdown():
    if tts:
        tts.playback.stop()
        tts.playback.join()
