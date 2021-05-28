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
from copy import deepcopy
import os
import random
import re
from abc import ABCMeta, abstractmethod
from threading import Thread
from time import time

import os.path
from os.path import dirname, exists, isdir, join

import mycroft.util
from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.metrics import report_timing, Stopwatch
from mycroft.util import (
    play_wav, play_mp3, check_for_signal, create_signal, resolve_resource_file
)
from mycroft.util.file_utils import get_temp_path
from mycroft.util.log import LOG
from mycroft.util.plugins import load_plugin
from queue import Queue, Empty
from .cache import hash_sentence, TextToSpeechCache


_TTS_ENV = deepcopy(os.environ)
_TTS_ENV['PULSE_PROP'] = 'media.role=phone'


EMPTY_PLAYBACK_QUEUE_TUPLE = (None, None, None, None, None)


class PlaybackThread(Thread):
    """Thread class for playing back tts audio and sending
    viseme data to enclosure.
    """

    def __init__(self, queue):
        super(PlaybackThread, self).__init__()
        self.queue = queue
        self._terminated = False
        self._processing_queue = False
        self.enclosure = None
        self.p = None
        # Check if the tts shall have a ducking role set
        if Configuration.get().get('tts', {}).get('pulse_duck'):
            self.pulse_env = _TTS_ENV
        else:
            self.pulse_env = None

    def init(self, tts):
        self.tts = tts

    def clear_queue(self):
        """Remove all pending playbacks."""
        while not self.queue.empty():
            self.queue.get()
        try:
            self.p.terminate()
        except Exception:
            pass

    def run(self):
        """Thread main loop. Get audio and extra data from queue and play.

        The queue messages is a tuple containing
        snd_type: 'mp3' or 'wav' telling the loop what format the data is in
        data: path to temporary audio data
        videmes: list of visemes to display while playing
        listen: if listening should be triggered at the end of the sentence.

        Playback of audio is started and the visemes are sent over the bus
        the loop then wait for the playback process to finish before starting
        checking the next position in queue.

        If the queue is empty the tts.end_audio() is called possibly triggering
        listening.
        """
        while not self._terminated:
            try:
                (snd_type, data,
                 visemes, ident, listen) = self.queue.get(timeout=2)
                self.blink(0.5)
                if not self._processing_queue:
                    self._processing_queue = True
                    self.tts.begin_audio()

                stopwatch = Stopwatch()
                with stopwatch:
                    if snd_type == 'wav':
                        self.p = play_wav(data, environment=self.pulse_env)
                    elif snd_type == 'mp3':
                        self.p = play_mp3(data, environment=self.pulse_env)
                    if visemes:
                        self.show_visemes(visemes)
                    if self.p:
                        self.p.communicate()
                        self.p.wait()
                report_timing(ident, 'speech_playback', stopwatch)

                if self.queue.empty():
                    self.tts.end_audio(listen)
                    self._processing_queue = False
                self.blink(0.2)
            except Empty:
                pass
            except Exception as e:
                LOG.exception(e)
                if self._processing_queue:
                    self.tts.end_audio(listen)
                    self._processing_queue = False

    def show_visemes(self, pairs):
        """Send viseme data to enclosure

        Arguments:
            pairs (list): Visime and timing pair

        Returns:
            bool: True if button has been pressed.
        """
        if self.enclosure:
            self.enclosure.mouth_viseme(time(), pairs)

    def clear(self):
        """Clear all pending actions for the TTS playback thread."""
        self.clear_queue()

    def blink(self, rate=1.0):
        """Blink mycroft's eyes"""
        if self.enclosure and random.random() < rate:
            self.enclosure.eyes_blink("b")

    def stop(self):
        """Stop thread"""
        self._terminated = True
        self.clear_queue()


class TTS(metaclass=ABCMeta):
    """TTS abstract class to be implemented by all TTS engines.

    It aggregates the minimum required parameters and exposes
    ``execute(sentence)`` and ``validate_ssml(sentence)`` functions.

    Arguments:
        lang (str):
        config (dict): Configuration for this specific tts engine
        validator (TTSValidator): Used to verify proper installation
        phonetic_spelling (bool): Whether to spell certain words phonetically
        ssml_tags (list): Supported ssml properties. Ex. ['speak', 'prosody']
    """

    def __init__(self, lang, config, validator, audio_ext='wav',
                 phonetic_spelling=True, ssml_tags=None):
        super(TTS, self).__init__()
        self.bus = None  # initalized in "init" step
        self.lang = lang or 'en-us'
        self.config = config
        self.validator = validator
        self.phonetic_spelling = phonetic_spelling
        self.audio_ext = audio_ext
        self.ssml_tags = ssml_tags or []

        self.voice = config.get("voice")
        self.filename = get_temp_path('tts.wav')
        self.enclosure = None
        random.seed()
        self.queue = Queue()
        self.playback = PlaybackThread(self.queue)
        self.playback.start()
        self.spellings = self.load_spellings()
        self.tts_name = type(self).__name__
        self.cache = TextToSpeechCache(
            self.config, self.tts_name, self.audio_ext
        )
        self.cache.clear()

    def load_spellings(self):
        """Load phonetic spellings of words as dictionary."""
        path = join('text', self.lang.lower(), 'phonetic_spellings.txt')
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
        """Helper function for child classes to call in execute()."""
        # Create signals informing start of speech
        self.bus.emit(Message("recognizer_loop:audio_output_start"))

    def end_audio(self, listen=False):
        """Helper function for child classes to call in execute().

        Sends the recognizer_loop:audio_output_end message (indicating
        that speaking is done for the moment) as well as trigger listening
        if it has been requested. It also checks if cache directory needs
        cleaning to free up disk space.

        Arguments:
            listen (bool): indication if listening trigger should be sent.
        """

        self.bus.emit(Message("recognizer_loop:audio_output_end"))
        if listen:
            self.bus.emit(Message('mycroft.mic.listen'))

        self.cache.curate()
        # This check will clear the "signal"
        check_for_signal("isSpeaking")

    def init(self, bus):
        """Performs intial setup of TTS object.

        Arguments:
            bus:    Mycroft messagebus connection
        """
        self.bus = bus
        self.playback.init(self)
        self.enclosure = EnclosureAPI(self.bus)
        self.playback.enclosure = self.enclosure

    def get_tts(self, sentence, wav_file):
        """Abstract method that a tts implementation needs to implement.

        Should get data from tts.

        Arguments:
            sentence(str): Sentence to synthesize
            wav_file(str): output file

        Returns:
            tuple: (wav_file, phoneme)
        """
        pass

    def modify_tag(self, tag):
        """Override to modify each supported ssml tag.

        Arguments:
            tag (str): SSML tag to check and possibly transform.
        """
        return tag

    @staticmethod
    def remove_ssml(text):
        """Removes SSML tags from a string.

        Arguments:
            text (str): input string

        Returns:
            str: input string stripped from tags.
        """
        return re.sub('<[^>]*>', '', text).replace('  ', ' ')

    def validate_ssml(self, utterance):
        """Check if engine supports ssml, if not remove all tags.

        Remove unsupported / invalid tags

        Arguments:
            utterance (str): Sentence to validate

        Returns:
            str: validated_sentence
        """
        # if ssml is not supported by TTS engine remove all tags
        if not self.ssml_tags:
            return self.remove_ssml(utterance)

        # find ssml tags in string
        tags = re.findall('<[^>]*>', utterance)

        for tag in tags:
            if any(supported in tag for supported in self.ssml_tags):
                utterance = utterance.replace(tag, self.modify_tag(tag))
            else:
                # remove unsupported tag
                utterance = utterance.replace(tag, "")

        # return text with supported ssml tags only
        return utterance.replace("  ", " ")

    def _preprocess_sentence(self, sentence):
        """Default preprocessing is no preprocessing.

        This method can be overridden to create chunks suitable to the
        TTS engine in question.

        Arguments:
            sentence (str): sentence to preprocess

        Returns:
            list: list of sentence parts
        """
        return [sentence]

    def execute(self, sentence, ident=None, listen=False):
        """Convert sentence to speech, preprocessing out unsupported ssml

        The method caches results if possible using the hash of the
        sentence.

        Arguments:
            sentence: (str) Sentence to be spoken
            ident: (str) Id reference to current interaction
            listen: (bool) True if listen should be triggered at the end
                    of the utterance.
        """
        sentence = self.validate_ssml(sentence)

        create_signal("isSpeaking")
        try:
            self._execute(sentence, ident, listen)
        except Exception:
            # If an error occurs end the audio sequence through an empty entry
            self.queue.put(EMPTY_PLAYBACK_QUEUE_TUPLE)
            # Re-raise to allow the Exception to be handled externally as well.
            raise

    def _execute(self, sentence, ident, listen):
        if self.phonetic_spelling:
            for word in re.findall(r"[\w']+", sentence):
                if word.lower() in self.spellings:
                    sentence = sentence.replace(word,
                                                self.spellings[word.lower()])

        chunks = self._preprocess_sentence(sentence)
        # Apply the listen flag to the last chunk, set the rest to False
        chunks = [(chunks[i], listen if i == len(chunks) - 1 else False)
                  for i in range(len(chunks))]

        for sentence, l in chunks:
            sentence_hash = hash_sentence(sentence)
            if sentence_hash in self.cache.cached_sentences:
                audio_file, phoneme_file = self._get_sentence_from_cache(
                    sentence_hash
                )
                if phoneme_file is None:
                    phonemes = None
                else:
                    phonemes = phoneme_file.load()

            else:
                # TODO: this should be changed return the audio data from
                #  the API call and then to call the add_to_cache method
                #  of the TTS cache.  But this requires changing the public
                #  API of the get_tts method in each engine.
                audio_file = self.cache.define_audio_file(sentence_hash)
                _, phonemes = self.get_tts(sentence, str(audio_file.path))
                if phonemes:
                    phoneme_file = self.cache.define_phoneme_file(
                        sentence_hash
                    )
                    phoneme_file.save(phonemes)
                else:
                    phoneme_file = None
                self.cache.cached_sentences[sentence_hash] = (
                    audio_file, phoneme_file
                )
            viseme = self.viseme(phonemes) if phonemes else None
            self.queue.put(
                (self.audio_ext, str(audio_file.path), viseme, ident, l)
            )

    def _get_sentence_from_cache(self, sentence_hash):
        cached_sentence = self.cache.cached_sentences[sentence_hash]
        audio_file, phoneme_file = cached_sentence
        LOG.info("Found {} in TTS cache".format(audio_file.name))

        return audio_file, phoneme_file

    def viseme(self, phonemes):
        """Create visemes from phonemes.

        May be implemented to convert TTS phonemes into Mycroft mouth
        visuals.

        Arguments:
            phonemes (str): String with phoneme data

        Returns:
            list: visemes
        """
        return None

    def clear_cache(self):
        """Remove all cached files."""
        # TODO: remove in 21.08
        LOG.warning("This method is deprecated, use TextToSpeechCache.clear")
        if not os.path.exists(mycroft.util.get_cache_directory('tts')):
            return
        for d in os.listdir(mycroft.util.get_cache_directory("tts")):
            dir_path = os.path.join(mycroft.util.get_cache_directory("tts"), d)
            if os.path.isdir(dir_path):
                for f in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, f)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
            # If no sub-folders are present, check if it is a file & clear it
            elif os.path.isfile(dir_path):
                os.unlink(dir_path)

    def save_phonemes(self, key, phonemes):
        """Cache phonemes

        Arguments:
            key (str):        Hash key for the sentence
            phonemes (str):   phoneme string to save
        """
        # TODO: remove in 21.08
        LOG.warning("This method is deprecated, use PhonemeFile.save")
        cache_dir = mycroft.util.get_cache_directory("tts/" + self.tts_name)
        pho_file = os.path.join(cache_dir, key + ".pho")
        try:
            with open(pho_file, "w") as cachefile:
                cachefile.write(phonemes)
        except Exception:
            LOG.exception("Failed to write {} to cache".format(pho_file))
            pass

    def load_phonemes(self, key):
        """Load phonemes from cache file.

        Arguments:
            key (str): Key identifying phoneme cache
        """
        # TODO: remove in 21.08
        LOG.warning("This method is deprecated, use PhonemeFile.load")
        pho_file = os.path.join(
            mycroft.util.get_cache_directory("tts/" + self.tts_name),
            key + ".pho")
        if os.path.exists(pho_file):
            try:
                with open(pho_file, "r") as cachefile:
                    phonemes = cachefile.read().strip()
                return phonemes
            except Exception:
                LOG.debug("Failed to read .PHO from cache")
        return None

    def __del__(self):
        self.playback.stop()
        self.playback.join()


class TTSValidator(metaclass=ABCMeta):
    """TTS Validator abstract class to be implemented by all TTS engines.

    It exposes and implements ``validate(tts)`` function as a template to
    validate the TTS engines.
    """

    def __init__(self, tts):
        self.tts = tts

    def validate(self):
        self.validate_dependencies()
        self.validate_instance()
        self.validate_filename()
        self.validate_lang()
        self.validate_connection()

    def validate_dependencies(self):
        """Determine if all the TTS's external dependencies are satisfied."""
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
        """Ensure the TTS supports current language."""

    @abstractmethod
    def validate_connection(self):
        """Ensure the TTS can connect to it's backend.

        This can mean for example being able to launch the correct executable
        or contact a webserver.
        """

    @abstractmethod
    def get_tts_class(self):
        """Return TTS class that this validator is for."""


def load_tts_plugin(module_name):
    """Wrapper function for loading tts plugin.

    Arguments:
        (str) Mycroft tts module name from config
    Returns:
        class: found tts plugin class
    """
    return load_plugin('mycroft.plugin.tts', module_name)


class TTSFactory:
    """Factory class instantiating the configured TTS engine.

    The factory can select between a range of built-in TTS engines and also
    from TTS engine plugins.
    """
    from mycroft.tts.festival_tts import Festival
    from mycroft.tts.espeak_tts import ESpeak
    from mycroft.tts.fa_tts import FATTS
    from mycroft.tts.google_tts import GoogleTTS
    from mycroft.tts.mary_tts import MaryTTS
    from mycroft.tts.mimic_tts import Mimic
    from mycroft.tts.spdsay_tts import SpdSay
    from mycroft.tts.bing_tts import BingTTS
    from mycroft.tts.ibm_tts import WatsonTTS
    from mycroft.tts.responsive_voice_tts import ResponsiveVoice
    from mycroft.tts.mimic2_tts import Mimic2
    from mycroft.tts.yandex_tts import YandexTTS
    from mycroft.tts.dummy_tts import DummyTTS
    from mycroft.tts.polly_tts import PollyTTS
    from mycroft.tts.mozilla_tts import MozillaTTS

    CLASSES = {
        "mimic": Mimic,
        "mimic2": Mimic2,
        "google": GoogleTTS,
        "marytts": MaryTTS,
        "fatts": FATTS,
        "festival": Festival,
        "espeak": ESpeak,
        "spdsay": SpdSay,
        "watson": WatsonTTS,
        "bing": BingTTS,
        "responsive_voice": ResponsiveVoice,
        "yandex": YandexTTS,
        "polly": PollyTTS,
        "mozilla": MozillaTTS,
        "dummy": DummyTTS
    }

    @staticmethod
    def create():
        """Factory method to create a TTS engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tts`` section with
        the name of a TTS module to be read by this method.

        "tts": {
            "module": <engine_name>
        }
        """
        config = Configuration.get()
        lang = config.get("lang", "en-us")
        tts_module = config.get('tts', {}).get('module', 'mimic')
        tts_config = config.get('tts', {}).get(tts_module, {})
        tts_lang = tts_config.get('lang', lang)
        try:
            if tts_module in TTSFactory.CLASSES:
                clazz = TTSFactory.CLASSES[tts_module]
            else:
                clazz = load_tts_plugin(tts_module)
                LOG.info('Loaded plugin {}'.format(tts_module))
            if clazz is None:
                raise ValueError('TTS module not found')

            tts = clazz(tts_lang, tts_config)
            tts.validator.validate()
        except Exception:
            # Fallback to mimic if an error occurs while loading.
            if tts_module != 'mimic':
                LOG.exception('The selected TTS backend couldn\'t be loaded. '
                              'Falling back to Mimic')
                clazz = TTSFactory.CLASSES.get('mimic')
                tts_config = config.get('tts', {}).get('mimic', {})
                tts = clazz(tts_lang, tts_config)
                tts.validator.validate()
            else:
                LOG.exception('The TTS could not be loaded.')
                raise
        return tts
