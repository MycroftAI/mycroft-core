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
"""Factory functions for loading hotword engines - both internal and plugins.
"""
from contextlib import suppress
from glob import glob
import os
from os.path import dirname, exists, join, abspath, expanduser, isfile, isdir
import platform
import posixpath
from shutil import rmtree
import struct
import tempfile
from threading import Timer, Thread
from time import time, sleep
from urllib.error import HTTPError
import xdg.BaseDirectory
import speech_recognition as sr

import requests

from mycroft.configuration import Configuration, BASE_FOLDER
from mycroft.util.log import LOG
from mycroft.util.monotonic_event import MonotonicEvent
from mycroft.util.plugins import load_plugin

RECOGNIZER_DIR = join(abspath(dirname(__file__)), "recognizer")
INIT_TIMEOUT = 10  # In seconds


class TriggerReload(Exception):
    pass


class NoModelAvailable(Exception):
    pass


class PreciseUnavailable(Exception):
    pass


def msec_to_sec(msecs):
    """Convert milliseconds to seconds.

    Args:
        msecs: milliseconds

    Returns:
        int: input converted from milliseconds to seconds
    """
    return msecs / 1000


class HotWordEngine:
    """Hotword/Wakeword base class to be implemented by all wake word plugins.

    Args:
        key_phrase (str): string representation of the wake word
        config (dict): Configuration block for the specific wake word
        lang (str): language code (BCP-47)
    """
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        self.key_phrase = str(key_phrase).lower()

        if config is None:
            config = Configuration.get().get("hot_words", {})
            config = config.get(self.key_phrase, {})
        self.config = config

        # rough estimate 1 phoneme per 2 chars
        self.num_phonemes = len(key_phrase) / 2 + 1
        phoneme_duration = msec_to_sec(config.get('phoneme_duration', 120))
        self.expected_duration = self.num_phonemes * phoneme_duration

        self.listener_config = Configuration.get().get("listener", {})
        self.lang = str(self.config.get("lang", lang)).lower()

    def found_wake_word(self, frame_data):
        """Check if wake word has been found.

        Checks if the wake word has been found. Should reset any internal
        tracking of the wake word state.

        Args:
            frame_data (binary data): Deprecated. Audio data for large chunk
                                      of audio to be processed. This should not
                                      be used to detect audio data instead
                                      use update() to incrementaly update audio
        Returns:
            bool: True if a wake word was detected, else False
        """
        return False

    def update(self, chunk):
        """Updates the hotword engine with new audio data.

        The engine should process the data and update internal trigger state.

        Args:
            chunk (bytes): Chunk of audio data to process
        """

    def stop(self):
        """Perform any actions needed to shut down the wake word engine.

        This may include things such as unloading data or shutdown
        external processess.
        """


class PocketsphinxHotWord(HotWordEngine):
    """Wake word engine using PocketSphinx.

    PocketSphinx is very general purpose but has a somewhat high error rate.
    The key advantage is to be able to specify the wake word with phonemes.
    """
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        super().__init__(key_phrase, config, lang)
        # Hotword module imports
        from pocketsphinx import Decoder
        # Hotword module params
        self.phonemes = self.config.get("phonemes", "HH EY . M AY K R AO F T")
        self.num_phonemes = len(self.phonemes.split())
        self.threshold = self.config.get("threshold", 1e-90)
        self.sample_rate = self.listener_config.get("sample_rate", 1600)
        dict_name = self.create_dict(self.key_phrase, self.phonemes)
        config = self.create_config(dict_name, Decoder.default_config())
        self.decoder = Decoder(config)

    def create_dict(self, key_phrase, phonemes):
        (fd, file_name) = tempfile.mkstemp()
        words = key_phrase.split()
        phoneme_groups = phonemes.split('.')
        with os.fdopen(fd, 'w') as f:
            for word, phoneme in zip(words, phoneme_groups):
                f.write(word + ' ' + phoneme + '\n')
        return file_name

    def create_config(self, dict_name, config):
        """If language config doesn't exist then
        we use default language (english) config as a fallback.
        """
        model_file = self.get_default_english_model()
        if self.lang != "en-us":
            LOG.error(
                'PocketSphinx model not found at "{}". '.format(model_file) +
                'Falling back to en-us model'
            )

        config.set_string('-hmm', model_file)
        config.set_string('-dict', dict_name)
        config.set_string('-keyphrase', self.key_phrase)
        config.set_float('-kws_threshold', float(self.threshold))
        config.set_float('-samprate', self.sample_rate)
        config.set_int('-nfft', 2048)
        config.set_string('-logfn', '/dev/null')
        return config

    def transcribe(self, byte_data, metrics=None):
        start = time()
        self.decoder.start_utt()
        self.decoder.process_raw(byte_data, False, False)
        self.decoder.end_utt()
        if metrics:
            metrics.timer("mycroft.stt.local.time_s", time() - start)
        return self.decoder.hyp()

    def found_wake_word(self, frame_data):
        hyp = self.transcribe(frame_data)
        return hyp and self.key_phrase in hyp.hypstr.lower()

    @staticmethod
    def get_default_english_model():
        language_directory = join(dirname(sr.__file__),
                                  "pocketsphinx-data", "en-US")
        return join(language_directory, "acoustic-model")


class PreciseHotword(HotWordEngine):
    """Precise is the default wake word engine for Mycroft.

    Precise is developed by Mycroft AI and produces quite good wake word
    spotting when trained on a decent dataset.
    """
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        super().__init__(key_phrase, config, lang)
        global install_package
        from petact import install_package
        from precise_runner import (
            PreciseRunner, PreciseEngine, ReadWriteStream
        )

        self.download_complete = True

        self.show_download_progress = Timer(0, lambda: None)
        precise_config = Configuration.get()['precise']

        precise_exe = self.update_precise(precise_config)

        local_model = self.config.get('local_model_file')
        if local_model:
            self.precise_model = expanduser(local_model)
        else:
            self.precise_model = self.install_model(
                precise_config['model_url'], key_phrase.replace(' ', '-')
            ).replace('.tar.gz', '.pb')

        self.has_found = False
        self.stream = ReadWriteStream()

        def on_activation():
            self.has_found = True

        trigger_level = self.config.get('trigger_level', 3)
        sensitivity = self.config.get('sensitivity', 0.5)

        self.runner = PreciseRunner(
            PreciseEngine(precise_exe, self.precise_model),
            trigger_level, sensitivity,
            stream=self.stream, on_activation=on_activation,
        )
        self.runner.start()

    def update_precise(self, precise_config):
        """Continously try to download precise until successful"""
        precise_exe = None
        while not precise_exe:
            try:
                precise_exe = self.install_exe(precise_config['dist_url'])
            except TriggerReload:
                raise
            except Exception as e:
                LOG.error(
                    'Precise could not be downloaded({})'.format(repr(e)))
                if exists(self.install_destination):
                    precise_exe = self.install_destination
                else:
                    # Wait one minute before retrying
                    sleep(60)
        return precise_exe

    @property
    def folder(self):
        old_path = join(expanduser('~'), '.' + BASE_FOLDER, 'precise')
        if os.path.isdir(old_path):
            return old_path
        return join(xdg.BaseDirectory.xdg_data_home, BASE_FOLDER, "precise")

    @property
    def install_destination(self):
        return join(self.folder, 'precise-engine', 'precise-engine')

    def install_exe(self, url: str) -> str:
        url = url.format(arch=platform.machine())
        if not url.endswith('.tar.gz'):
            url = requests.get(url).text.strip()
        if install_package(
                url, self.folder,
                on_download=self.on_download, on_complete=self.on_complete
        ):
            raise TriggerReload
        return self.install_destination

    def install_model(self, url: str, wake_word: str) -> str:
        model_url = url.format(wake_word=wake_word)
        model_file = join(self.folder, posixpath.basename(model_url))
        try:
            install_package(
                model_url, self.folder,
                on_download=lambda: LOG.info('Updated precise model')
            )
        except (HTTPError, ValueError):
            if isfile(model_file):
                LOG.info("Couldn't find remote model.  Using local file")
            else:
                raise NoModelAvailable('Failed to download model:', model_url)
        return model_file

    @staticmethod
    def _snd_msg(cmd):
        with suppress(OSError):
            with open('/dev/ttyAMA0', 'w') as f:
                print(cmd, file=f)

    def on_download(self):
        LOG.info('Downloading Precise executable...')
        if isdir(join(self.folder, 'precise-stream')):
            rmtree(join(self.folder, 'precise-stream'))
        for old_package in glob(join(self.folder, 'precise-engine_*.tar.gz')):
            os.remove(old_package)
        self.download_complete = False
        self.show_download_progress = Timer(
            5, self.during_download, args=[True]
        )
        self.show_download_progress.start()

    def during_download(self, first_run=False):
        LOG.info('Still downloading executable...')
        if first_run:  # TODO: Localize
            self._snd_msg('mouth.text=Updating listener...')
        if not self.download_complete:
            self.show_download_progress = Timer(30, self.during_download)
            self.show_download_progress.start()

    def on_complete(self):
        LOG.info('Precise download complete!')
        self.download_complete = True
        self.show_download_progress.cancel()
        self._snd_msg('mouth.reset')

    def update(self, chunk):
        self.stream.write(chunk)

    def found_wake_word(self, frame_data):
        if self.has_found:
            self.has_found = False
            return True
        return False

    def stop(self):
        if self.runner:
            self.runner.stop()


class SnowboyHotWord(HotWordEngine):
    """Snowboy is a thirdparty wake word engine providing an easy training and
    testing interface.
    """
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        super().__init__(key_phrase, config, lang)
        # Hotword module imports
        from snowboydecoder import HotwordDetector
        # Hotword module config
        module = self.config.get("module")
        if module != "snowboy":
            LOG.warning(module + " module does not match with Hotword class "
                                 "snowboy")
        # Hotword params
        models = self.config.get("models", {})
        paths = []
        for key in models:
            paths.append(models[key])
        sensitivity = self.config.get("sensitivity", 0.5)
        self.snowboy = HotwordDetector(paths,
                                       sensitivity=[sensitivity] * len(paths))
        self.lang = str(lang).lower()
        self.key_phrase = str(key_phrase).lower()

    def found_wake_word(self, frame_data):
        wake_word = self.snowboy.detector.RunDetection(frame_data)
        return wake_word >= 1


class PorcupineHotWord(HotWordEngine):
    """Hotword engine using picovoice's Porcupine hot word engine.

    TODO: Remove in 21.02
    """
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        super().__init__(key_phrase, config, lang)
        keyword_file_paths = [expanduser(x.strip()) for x in self.config.get(
            "keyword_file_path", "hey_mycroft.ppn").split(',')]
        sensitivities = self.config.get("sensitivities", 0.5)

        try:
            from pvporcupine.porcupine import Porcupine
            from pvporcupine.util import (pv_library_path,
                                          pv_model_path)
        except ImportError as err:
            raise Exception(
                "Python bindings for Porcupine not found. "
                "Please run \"mycroft-pip install pvporcupine\"") from err

        library_path = pv_library_path('')
        model_file_path = pv_model_path('')
        if isinstance(sensitivities, float):
            sensitivities = [sensitivities] * len(keyword_file_paths)
        else:
            sensitivities = [float(x) for x in sensitivities.split(',')]

        self.audio_buffer = []
        self.has_found = False
        self.num_keywords = len(keyword_file_paths)

        LOG.warning('The Porcupine wakeword engine shipped with '
                    'Mycroft-core is deprecated and will be removed in '
                    'mycroft-core 21.02. Use the mycroft-porcupine-plugin '
                    'instead.')
        LOG.info(
            'Loading Porcupine using library path {} and keyword paths {}'
            .format(library_path, keyword_file_paths))
        self.porcupine = Porcupine(
            library_path=library_path,
            model_path=model_file_path,
            keyword_paths=keyword_file_paths,
            sensitivities=sensitivities)

        LOG.info('Loaded Porcupine')

    def update(self, chunk):
        """Update detection state from a chunk of audio data.

        Args:
            chunk (bytes): Audio data to parse
        """
        pcm = struct.unpack_from("h" * (len(chunk)//2), chunk)
        self.audio_buffer += pcm
        while True:
            if len(self.audio_buffer) >= self.porcupine.frame_length:
                result = self.porcupine.process(
                    self.audio_buffer[0:self.porcupine.frame_length])
                # result will be the index of the found keyword or -1 if
                # nothing has been found.
                self.has_found |= result >= 0
                self.audio_buffer = self.audio_buffer[
                    self.porcupine.frame_length:]
            else:
                return

    def found_wake_word(self, frame_data):
        """Check if wakeword has been found.

        Returns:
            (bool) True if wakeword was found otherwise False.
        """
        if self.has_found:
            self.has_found = False
            return True
        return False

    def stop(self):
        """Stop the hotword engine.

        Clean up Porcupine library.
        """
        if self.porcupine is not None:
            self.porcupine.delete()


def load_wake_word_plugin(module_name):
    """Wrapper function for loading wake word plugin.

    Args:
        (str) Mycroft wake word module name from config
    """
    return load_plugin('mycroft.plugin.wake_word', module_name)


class HotWordFactory:
    """Factory class instantiating the configured Hotword engine.

    The factory can select between a range of built-in Hotword engines and also
    from Hotword engine plugins.
    """
    CLASSES = {
        "pocketsphinx": PocketsphinxHotWord,
        "precise": PreciseHotword,
        "snowboy": SnowboyHotWord,
        "porcupine": PorcupineHotWord
    }

    @staticmethod
    def load_module(module, hotword, config, lang, loop):
        LOG.info('Loading "{}" wake word via {}'.format(hotword, module))
        instance = None
        complete = MonotonicEvent()

        def initialize():
            nonlocal instance, complete
            try:
                if module in HotWordFactory.CLASSES:
                    clazz = HotWordFactory.CLASSES[module]
                else:
                    clazz = load_wake_word_plugin(module)
                    LOG.info('Loaded the Wake Word plugin {}'.format(module))

                instance = clazz(hotword, config, lang=lang)
            except TriggerReload:
                complete.set()
                sleep(0.5)
                loop.reload()
            except NoModelAvailable:
                LOG.warning('Could not found find model for {} on {}.'.format(
                    hotword, module
                ))
                instance = None
            except PreciseUnavailable:
                LOG.warning('Settings prevent Precise Engine use, '
                            'falling back to default.')
                instance = None
            except Exception:
                LOG.exception(
                    'Could not create hotword. Falling back to default.')
                instance = None
            complete.set()

        Thread(target=initialize, daemon=True).start()
        if not complete.wait(INIT_TIMEOUT):
            LOG.info('{} is taking too long to load'.format(module))
            complete.set()
        return instance

    @classmethod
    def create_hotword(cls, hotword="hey mycroft", config=None,
                       lang="en-us", loop=None):
        if not config:
            config = Configuration.get()['hotwords']
        config = config.get(hotword) or config["hey mycroft"]

        module = config.get("module", "precise")
        return cls.load_module(module, hotword, config, lang, loop) or \
            cls.load_module('pocketsphinx', hotword, config, lang, loop) or \
            cls.CLASSES['pocketsphinx']()
