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
import hashlib
import random
from threading import Thread
from time import time, sleep

import re
import os
import os.path
from abc import ABCMeta, abstractmethod
from os.path import dirname, exists, isdir, join

import mycroft.util
from mycroft.client.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util import (
    play_wav, play_mp3, check_for_signal, create_signal, resolve_resource_file
)
from mycroft.util.log import LOG
from mycroft.metrics import report_timing, Stopwatch
from queue import Queue, Empty


def send_playback_metric(stopwatch, ident):
    """
        Send playback metrics in a background thread
    """
    def do_send(stopwatch, ident):
        report_timing(ident, 'speech_playback', stopwatch)

    t = Thread(target=do_send, args=(stopwatch, ident))
    t.daemon = True
    t.start()


class PlaybackThread(Thread):
    """
        Thread class for playing back tts audio and sending
        visime data to enclosure.
    """

    def __init__(self, queue):
        super(PlaybackThread, self).__init__()
        self.queue = queue
        self._terminated = False
        self._processing_queue = False
        self._clear_visimes = False

    def init(self, tts):
        self.tts = tts

    def clear_queue(self):
        """
            Remove all pending playbacks.
        """
        while not self.queue.empty():
            self.queue.get()
        try:
            self.p.terminate()
        except:
            pass

    def run(self):
        """
            Thread main loop. get audio and visime data from queue
            and play.
        """
        while not self._terminated:
            try:
                snd_type, data, visimes, ident = self.queue.get(timeout=2)
                self.blink(0.5)
                if not self._processing_queue:
                    self._processing_queue = True
                    self.tts.begin_audio()

                stopwatch = Stopwatch()
                with stopwatch:
                    if snd_type == 'wav':
                        self.p = play_wav(data)
                    elif snd_type == 'mp3':
                        self.p = play_mp3(data)

                    if visimes:
                        if self.show_visimes(visimes):
                            self.clear_queue()
                    else:
                        self.p.communicate()
                    self.p.wait()
                send_playback_metric(stopwatch, ident)

                if self.queue.empty():
                    self.tts.end_audio()
                    self._processing_queue = False
                self.blink(0.2)
            except Empty:
                pass
            except Exception as e:
                LOG.exception(e)
                if self._processing_queue:
                    self.tts.end_audio()
                    self._processing_queue = False

    def show_visimes(self, pairs):
        """
            Send visime data to enclosure

            Args:
                pairs(list): Visime and timing pair

            Returns:
                True if button has been pressed.
        """
        start = time()
        for code, duration in pairs:
            if self._clear_visimes:
                self._clear_visimes = False
                return True
            if self.enclosure:
                # Include time stamp to assist with animation timing
                self.enclosure.mouth_viseme(code, start+duration)
            delta = time() - start
            if delta < duration:
                sleep(duration - delta)
        return False

    def clear_visimes(self):
        self._clear_visimes = True

    def blink(self, rate=1.0):
        """ Blink mycroft's eyes """
        if self.enclosure and random.random() < rate:
            self.enclosure.eyes_blink("b")

    def stop(self):
        """ Stop thread """
        self._terminated = True
        self.clear_queue()


class TTS(object):
    """
    TTS abstract class to be implemented by all TTS engines.

    It aggregates the minimum required parameters and exposes
    ``execute(sentence)`` function.
    """
    __metaclass__ = ABCMeta

    def __init__(self, lang, voice, validator, phonetic_spelling=True):
        super(TTS, self).__init__()
        self.lang = lang or 'en-us'
        self.voice = voice
        self.filename = '/tmp/tts.wav'
        self.validator = validator
        self.phonetic_spelling = phonetic_spelling
        self.enclosure = None
        random.seed()
        self.queue = Queue()
        self.playback = PlaybackThread(self.queue)
        self.playback.start()
        self.clear_cache()
        self.spellings = self.load_spellings()

    def load_spellings(self):
        """Load phonetic spellings of words as dictionary"""
        path = join('text', self.lang, 'phonetic_spellings.txt')
        spellings_file = resolve_resource_file(path)
        if not spellings_file:
            return {}
        try:
            with open(spellings_file) as f:
                lines = filter(bool, f.read().split('\n'))
            lines = [i.split(':') for i in lines]
            return {key.strip(): value.strip() for key, value in lines}
        except ValueError:
            LOG.exception('Failed to load phonetic spellings.')
            return {}

    def begin_audio(self):
        """Helper function for child classes to call in execute()"""
        # Create signals informing start of speech
        self.ws.emit(Message("recognizer_loop:audio_output_start"))

    def end_audio(self):
        """
            Helper function for child classes to call in execute().

            Sends the recognizer_loop:audio_output_end message, indicating
            that speaking is done for the moment. It also checks if cache
            directory needs cleaning to free up disk space.
        """

        self.ws.emit(Message("recognizer_loop:audio_output_end"))
        # Clean the cache as needed
        cache_dir = mycroft.util.get_cache_directory("tts")
        mycroft.util.curate_cache(cache_dir, min_free_percent=100)

        # This check will clear the "signal"
        check_for_signal("isSpeaking")

    def init(self, ws):
        self.ws = ws
        self.playback.init(self)
        self.enclosure = EnclosureAPI(self.ws)
        self.playback.enclosure = self.enclosure

    def get_tts(self, sentence, wav_file):
        """
            Abstract method that a tts implementation needs to implement.
            Should get data from tts.

            Args:
                sentence(str): Sentence to synthesize
                wav_file(str): output file

            Returns: (wav_file, phoneme) tuple
        """
        pass

    def execute(self, sentence, ident=None):
        """
            Convert sentence to speech.

            The method caches results if possible using the hash of the
            sentence.

            Args:
                sentence:   Sentence to be spoken
                ident:      Id reference to current interaction
        """
        create_signal("isSpeaking")
        if self.phonetic_spelling:
            for word in re.findall(r"[\w']+", sentence):
                if word in self.spellings:
                    sentence = sentence.replace(word, self.spellings[word])

        key = str(hashlib.md5(sentence.encode('utf-8', 'ignore')).hexdigest())
        wav_file = os.path.join(mycroft.util.get_cache_directory("tts"),
                                key + '.' + self.type)

        if os.path.exists(wav_file):
            LOG.debug("TTS cache hit")
            phonemes = self.load_phonemes(key)
        else:
            wav_file, phonemes = self.get_tts(sentence, wav_file)
            if phonemes:
                self.save_phonemes(key, phonemes)

        self.queue.put((self.type, wav_file, self.visime(phonemes), ident))

    def visime(self, phonemes):
        """
            Create visimes from phonemes. Needs to be implemented for all
            tts backend

            Args:
                phonemes(str): String with phoneme data
        """
        return None

    def clear_cache(self):
        """ Remove all cached files. """
        if not os.path.exists(mycroft.util.get_cache_directory('tts')):
            return
        for f in os.listdir(mycroft.util.get_cache_directory("tts")):
            file_path = os.path.join(mycroft.util.get_cache_directory("tts"),
                                     f)
            if os.path.isfile(file_path):
                os.unlink(file_path)

    def save_phonemes(self, key, phonemes):
        """
            Cache phonemes

            Args:
                key:        Hash key for the sentence
                phonemes:   phoneme string to save
        """

        cache_dir = mycroft.util.get_cache_directory("tts")
        pho_file = os.path.join(cache_dir, key + ".pho")
        try:
            with open(pho_file, "w") as cachefile:
                cachefile.write(phonemes)
        except:
            LOG.debug("Failed to write .PHO to cache")
            pass

    def load_phonemes(self, key):
        """
            Load phonemes from cache file.

            Args:
                Key:    Key identifying phoneme cache
        """
        pho_file = os.path.join(mycroft.util.get_cache_directory("tts"),
                                key + ".pho")
        if os.path.exists(pho_file):
            try:
                with open(pho_file, "r") as cachefile:
                    phonemes = cachefile.read().strip()
                return phonemes
            except:
                LOG.debug("Failed to read .PHO from cache")
        return None

    def __del__(self):
        self.playback.stop()
        self.playback.join()


class TTSValidator(object):
    """
    TTS Validator abstract class to be implemented by all TTS engines.

    It exposes and implements ``validate(tts)`` function as a template to
    validate the TTS engines.
    """
    __metaclass__ = ABCMeta

    def __init__(self, tts):
        self.tts = tts

    def validate(self):
        self.validate_dependencies()
        self.validate_instance()
        self.validate_filename()
        self.validate_lang()
        self.validate_connection()

    def validate_dependencies(self):
        pass

    def validate_instance(self):
        clazz = self.get_tts_class()
        if not isinstance(self.tts, clazz):
            raise AttributeError('tts must be instance of ' + clazz.__name__)

    def validate_filename(self):
        filename = self.tts.filename
        if not (filename and filename.endswith('.wav')):
            raise AttributeError('file: %s must be in .wav format!' % filename)

        dir_path = dirname(filename)
        if not (exists(dir_path) and isdir(dir_path)):
            raise AttributeError('filename: %s is not valid!' % filename)

    @abstractmethod
    def validate_lang(self):
        pass

    @abstractmethod
    def validate_connection(self):
        pass

    @abstractmethod
    def get_tts_class(self):
        pass


class TTSFactory(object):
    from mycroft.tts.espeak_tts import ESpeak
    from mycroft.tts.fa_tts import FATTS
    from mycroft.tts.google_tts import GoogleTTS
    from mycroft.tts.mary_tts import MaryTTS
    from mycroft.tts.mimic_tts import Mimic
    from mycroft.tts.spdsay_tts import SpdSay
    from mycroft.tts.bing_tts import BingTTS
    from mycroft.tts.ibm_tts import WatsonTTS

    CLASSES = {
        "mimic": Mimic,
        "google": GoogleTTS,
        "marytts": MaryTTS,
        "fatts": FATTS,
        "espeak": ESpeak,
        "spdsay": SpdSay,
        "watson": WatsonTTS,
        "bing": BingTTS
    }

    @staticmethod
    def create():
        """
        Factory method to create a TTS engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tts`` section with
        the name of a TTS module to be read by this method.

        "tts": {
            "module": <engine_name>
        }
        """

        from mycroft.tts.remote_tts import RemoteTTS
        config = Configuration.get().get('tts', {})
        module = config.get('module', 'mimic')
        lang = config.get(module).get('lang')
        voice = config.get(module).get('voice')
        clazz = TTSFactory.CLASSES.get(module)

        if issubclass(clazz, RemoteTTS):
            url = config.get(module).get('url')
            tts = clazz(lang, voice, url)
        else:
            tts = clazz(lang, voice)

        tts.validator.validate()
        return tts
