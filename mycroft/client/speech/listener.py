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
import json
import time
from queue import Queue, Empty
from threading import Thread

import pyaudio
from pyee import EventEmitter

from mycroft.client.speech.hotword_factory import HotWordFactory
from mycroft.client.speech.mic import MutableMicrophone, ResponsiveRecognizer
from mycroft.configuration import Configuration
from mycroft.metrics import Stopwatch, report_timing
from mycroft.session import SessionManager
from mycroft.stt import STTFactory
from mycroft.util import find_input_device
from mycroft.util.log import LOG

MAX_MIC_RESTARTS = 20

AUDIO_DATA = 0
STREAM_START = 1
STREAM_DATA = 2
STREAM_STOP = 3


class AudioStreamHandler:
    def __init__(self, queue):
        self.queue = queue

    def stream_start(self):
        self.queue.put((STREAM_START, None))

    def stream_chunk(self, chunk):
        self.queue.put((STREAM_DATA, chunk))

    def stream_stop(self):
        self.queue.put((STREAM_STOP, None))


class AudioProducer(Thread):
    """AudioProducer
    Given a mic and a recognizer implementation, continuously listens to the
    mic for potential speech chunks and pushes them onto the queue.
    """

    def __init__(self, loop):
        super(AudioProducer, self).__init__()
        self.daemon = True
        self.loop = loop
        self.stream_handler = None
        if self.loop.stt.can_stream:
            self.stream_handler = AudioStreamHandler(self.loop.queue)

    def run(self):
        restart_attempts = 0
        with self.loop.microphone as source:
            self.loop.responsive_recognizer.adjust_for_ambient_noise(source)
            while self.loop.state.running:
                try:
                    audio, lang = self.loop.responsive_recognizer.listen(
                        source, self.stream_handler)
                    if audio is not None:
                        self.loop.queue.put((AUDIO_DATA, audio, lang))
                    else:
                        LOG.warning("Audio contains no data.")
                except IOError as e:
                    # IOError will be thrown if the read is unsuccessful.
                    # If self.recognizer.overflow_exc is False (default)
                    # input buffer overflow IOErrors due to not consuming the
                    # buffers quickly enough will be silently ignored.
                    LOG.error('IOError Exception in AudioProducer')
                    if e.errno == pyaudio.paInputOverflowed:
                        pass  # Ignore overflow errors
                    elif restart_attempts < MAX_MIC_RESTARTS:
                        # restart the mic
                        restart_attempts += 1
                        LOG.debug('Restarting the microphone...')
                        source.restart()
                        LOG.debug('Restarted...')
                    else:
                        LOG.error('Restarting mic doesn\'t seem to work. '
                                  'Stopping...')
                        raise
                except Exception:
                    LOG.exception("error in audio producer")
                    source.restart()
                    LOG.debug('Mic Restarted.')
                    # raise
                else:
                    # Reset restart attempt counter on sucessful audio read
                    restart_attempts = 0
                finally:
                    if self.stream_handler is not None:
                        self.stream_handler.stream_stop()

    def stop(self):
        """Stop producer thread."""
        self.loop.state.running = False
        self.loop.responsive_recognizer.stop()


class AudioConsumer(Thread):
    """AudioConsumer
    Consumes AudioData chunks off the queue
    """

    # In seconds, the minimum audio size to be sent to remote STT
    MIN_AUDIO_SIZE = 0.5

    def __init__(self, loop):
        super(AudioConsumer, self).__init__()
        self.daemon = True
        self.loop = loop

    @property
    def wakeup_engines(self):
        """ wake from sleep mode """
        return [(ww, w["engine"]) for ww, w in self.loop.engines.items()
                if w["wakeup"]]

    def run(self):
        while self.loop.state.running:
            self.read()

    def read(self):
        try:
            message = self.loop.queue.get(timeout=0.5)
        except Empty:
            return

        if message is None:
            return

        tag, data, lang = message

        if tag == AUDIO_DATA:
            if data is not None and not self.loop.state.sleeping:
                self.process(data)
        elif tag == STREAM_START:
            self.loop.stt.stream_start()
        elif tag == STREAM_DATA:
            self.loop.stt.stream_data(data)
        elif tag == STREAM_STOP:
            self.loop.stt.stream_stop()
        else:
            LOG.error("Unknown audio queue type %r" % message)

    @staticmethod
    def _audio_length(audio):
        return float(len(audio.frame_data)) / (
                audio.sample_rate * audio.sample_width)

    def process(self, audio, lang=None):
        if audio is None:
            return

        if self._audio_length(audio) < self.MIN_AUDIO_SIZE:
            LOG.warning("Audio too short to be processed")
        else:
            stopwatch = Stopwatch()
            with stopwatch:
                transcription = self.transcribe(audio, lang)
            if transcription:
                ident = str(stopwatch.timestamp) + str(hash(transcription))
                # STT succeeded, send the transcribed speech on for processing
                payload = {
                    'utterances': [transcription],
                    'lang': self.loop.stt.lang,
                    'session': SessionManager.get().session_id,
                    'ident': ident
                }
                self.loop.emit("recognizer_loop:utterance", payload)

                # Report timing metrics
                report_timing(ident, 'stt', stopwatch,
                              {'transcription': transcription,
                               'stt': self.loop.stt.__class__.__name__})
            else:
                ident = str(stopwatch.timestamp)

    def transcribe(self, audio, lang):
        def send_unknown_intent():
            """ Send message that nothing was transcribed. """
            self.loop.emit('recognizer_loop:speech.recognition.unknown')

        try:
            # Invoke the STT engine on the audio clip
            try:
                text = self.loop.stt.execute(audio, language=lang)
            except Exception as e:
                if self.loop.fallback_stt:
                    LOG.warning(f"Using fallback STT, main plugin failed: {e}")
                    text = self.loop.fallback_stt.execute(audio, language=lang)
                else:
                    raise e
            if text is not None:
                text = text.lower().strip()
                LOG.debug("STT: " + text)
            else:
                send_unknown_intent()
                LOG.info('no words were transcribed')
            return text
        except Exception as e:
            send_unknown_intent()
            LOG.exception("Speech Recognition could not understand audio")
            return None


class RecognizerLoopState:
    def __init__(self):
        self.running = False
        self.sleeping = False


def recognizer_conf_hash(config):
    """Hash of the values important to the listener."""
    c = {
        'listener': config.get('listener'),
        'hotwords': config.get('hotwords'),
        'stt': config.get('stt'),
        'opt_in': config.get('opt_in', False)
    }
    return hash(json.dumps(c, sort_keys=True))


class RecognizerLoop(EventEmitter):
    """ EventEmitter loop running speech recognition.

    Local wake word recognizer and remote general speech recognition.

    Args:
        bus (MessageBusClient): mycroft messagebus connection
        watchdog: (callable) function to call periodically indicating
                  operational status.
        stt (STT): stt plugin to be used for inference
                (optional, can be set later via self.bind )
    """

    def __init__(self, bus, watchdog=None, stt=None, fallback_stt=None):
        super(RecognizerLoop, self).__init__()
        self._watchdog = watchdog
        self.mute_calls = 0
        self.stt = stt
        self.fallback_stt = fallback_stt
        self.bus = bus
        self.engines = {}
        self.queue = None
        self.audio_consumer = None
        self.audio_producer = None
        self.responsive_recognizer = None

        self._load_config()

    def bind(self, stt, fallback_stt=None):
        self.stt = stt
        if fallback_stt:
            self.fallback_stt = fallback_stt

    def _load_config(self):
        """Load configuration parameters from configuration."""
        config = Configuration.get()
        self.config_core = config
        self._config_hash = recognizer_conf_hash(config)
        self.lang = config.get('lang')
        self.config = config.get('listener')
        rate = self.config.get('sample_rate')

        device_index = self.config.get('device_index')
        device_name = self.config.get('device_name')
        if not device_index and device_name:
            device_index = find_input_device(device_name)

        LOG.debug('Using microphone (None = default): ' + str(device_index))

        self.microphone = MutableMicrophone(device_index, rate,
                                            mute=self.mute_calls > 0)
        self.create_hotword_engines()
        self.state = RecognizerLoopState()
        self.responsive_recognizer = ResponsiveRecognizer(self)

    def create_hotword_engines(self):
        LOG.info("creating hotword engines")
        hot_words = self.config_core.get("hotwords", {})
        global_listen = self.config_core.get("confirm_listening")
        global_sounds = self.config_core.get("sounds", {})
        for word in hot_words:
            try:
                data = hot_words[word]
                sound = data.get("sound")
                utterance = data.get("utterance")
                listen = data.get("listen", False)
                wakeup = data.get("wakeup", False)
                trigger = data.get("trigger", False)
                lang = data.get("stt_lang", self.lang)
                enabled = data.get("active", True)
                event = data.get("bus_event")
                # global listening sound
                if not sound and listen and global_listen:
                    sound = global_sounds.get("start_listening")

                if not enabled:
                    continue
                engine = HotWordFactory.create_hotword(word,
                                                       lang=lang,
                                                       loop=self)
                if engine is not None:
                    if hasattr(engine, "bind"):
                        engine.bind(self.bus)
                        # not all plugins implement this
                    self.engines[word] = {"engine": engine,
                                          "sound": sound,
                                          "bus_event": event,
                                          "trigger": trigger,
                                          "utterance": utterance,
                                          "stt_lang": lang,
                                          "listen": listen,
                                          "wakeup": wakeup}
            except Exception as e:
                LOG.error("Failed to load hotword: " + word)

    @staticmethod
    def get_fallback_stt():
        config_core = Configuration.get()
        stt_config = config_core.get('stt', {})
        engine = stt_config.get("fallback_module")
        if not engine:
            LOG.warning("No fallback STT configured")
        else:
            plugin_config = stt_config.get(engine) or {}
            plugin_config["lang"] = plugin_config.get("lang") or \
                                    config_core.get("lang", "en-us")
            clazz = STTFactory.get_class({"module": engine,
                                             engine: plugin_config})
            if clazz:
                return clazz
            else:
                LOG.warning(f"Could not find plugin: {engine}")
        LOG.error(f"Failed to create fallback STT")

    def start_async(self):
        """Start consumer and producer threads."""
        self.state.running = True
        if not self.stt:
            self.stt = STTFactory.create()
        if not self.fallback_stt:
            clazz = self.get_fallback_stt()
            self.fallback_stt = clazz()

        self.queue = Queue()
        self.audio_consumer = AudioConsumer(self)
        self.audio_consumer.start()
        self.audio_producer = AudioProducer(self)
        self.audio_producer.start()

    def stop(self):
        self.state.running = False
        self.audio_producer.stop()
        # stop wake word detectors
        for ww, hotword in self.engines.items():
            hotword["engine"].stop()
        # wait for threads to shutdown
        self.audio_producer.join()
        self.audio_consumer.join()

    def mute(self):
        """Mute microphone and increase number of requests to mute."""
        self.mute_calls += 1
        if self.microphone:
            self.microphone.mute()

    def unmute(self):
        """Unmute mic if as many unmute calls as mute calls have been received.
        """
        if self.mute_calls > 0:
            self.mute_calls -= 1

        if self.mute_calls <= 0 and self.microphone:
            self.microphone.unmute()
            self.mute_calls = 0

    def force_unmute(self):
        """Completely unmute mic regardless of the number of calls to mute."""
        self.mute_calls = 0
        self.unmute()

    def is_muted(self):
        if self.microphone:
            return self.microphone.is_muted()
        else:
            return True  # consider 'no mic' muted

    def sleep(self):
        self.state.sleeping = True

    def awaken(self):
        self.state.sleeping = False

    def run(self):
        """Start and reload mic and STT handling threads as needed.

        Wait for KeyboardInterrupt and shutdown cleanly.
        """
        try:
            self.start_async()
        except Exception:
            LOG.exception('Starting producer/consumer threads for listener '
                          'failed.')
            return

        # Handle reload of consumer / producer if config changes
        while self.state.running:
            try:
                time.sleep(1)
                current_hash = recognizer_conf_hash(Configuration().get())
                if current_hash != self._config_hash:
                    self._config_hash = current_hash
                    LOG.debug('Config has changed, reloading...')
                    self.reload()
            except KeyboardInterrupt as e:
                LOG.error(e)
                self.stop()
                raise  # Re-raise KeyboardInterrupt
            except Exception:
                LOG.exception('Exception in RecognizerLoop')
                raise

    def reload(self):
        """Reload configuration and restart consumer and producer."""
        self.stop()
        # load config
        self._load_config()
        # restart
        self.start_async()
