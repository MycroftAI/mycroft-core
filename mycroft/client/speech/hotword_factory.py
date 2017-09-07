from mycroft.configuration import ConfigurationManager
from mycroft.util.log import getLogger
from os.path import dirname, exists, join, abspath
import os
import time
import tempfile

__author__ = 'seanfitz, jdorleans, jarbas'

LOG = getLogger("HotwordFactory")

BASEDIR = dirname(abspath(__file__)).join("recognizer")


class PocketsphinxHotWord():
    def __init__(self, key_phrase, lang="en-us", config=None):
        if config is None:
            config = ConfigurationManager.get().get("hot_words", {})
            config = config.get(key_phrase, {})
        # Hotword module imports
        from pocketsphinx import Decoder
        # Hotword module config
        module = config.get("module")
        if module != "pocketsphinx":
            LOG.warning("module does not match with Hotword class")
        # Hotword module params
        self.phonemes = config.get("phonemes", "HH EY . M AY K R AO F T")
        self.threshold = config.get("threshold", 1e-90)
        self.sample_rate = config.get("sample_rate", 1600)
        self.lang = str(lang).lower()
        self.key_phrase = str(key_phrase).lower()
        dict_name = self.create_dict(key_phrase, self.phonemes)
        self.decoder = Decoder(self.create_config(dict_name, Decoder))

    def create_dict(self, key_phrase, phonemes):
        (fd, file_name) = tempfile.mkstemp()
        words = key_phrase.split()
        phoneme_groups = phonemes.split('.')
        with os.fdopen(fd, 'w') as f:
            for word, phoneme in zip(words, phoneme_groups):
                f.write(word + ' ' + phoneme + '\n')
        return file_name

    def create_config(self, dict_name, Decoder):
        config = Decoder.default_config()
        model_file = join(BASEDIR, 'model', self.lang, 'hmm')
        if not exists(model_file):
            LOG.error('PocketSphinx model not found for {}', self.lang)
            model_file = join(BASEDIR, 'model', 'en-us', 'hmm')

        config.set_string('-hmm', model_file)
        config.set_string('-dict', dict_name)
        config.set_string('-keyphrase', self.key_phrase)
        config.set_float('-kws_threshold', float(self.threshold))
        config.set_float('-samprate', self.sample_rate)
        config.set_int('-nfft', 2048)
        config.set_string('-logfn', '/dev/null')
        return config

    def transcribe(self, byte_data, metrics=None):
        start = time.time()
        self.decoder.start_utt()
        self.decoder.process_raw(byte_data, False, False)
        self.decoder.end_utt()
        if metrics:
            metrics.timer("mycroft.stt.local.time_s", time.time() - start)
        return self.decoder.hyp()

    def found_wake_word(self, frame_data):
        hyp = self.transcribe(frame_data)
        return hyp and self.key_phrase in hyp.hypstr.lower()


class SnowboyHotWord():
    def __init__(self, key_phrase, lang="en-us", config=None):
        if config is None:
            config = ConfigurationManager.get().get("hot_words", {})
            config = config.get(key_phrase, {})
        # Hotword module imports
        from snowboydecoder import HotwordDetector
        # Hotword module config
        module = config.get("module")
        if module != "snowboy":
            LOG.warning(module + " module does not match with Hotword class "
                                 "snowboy")
        # Hotword params
        models = config.get("models", {})
        paths = []
        for key in models:
            paths.append(models[key])
        sensitivity = config.get("sensitivity", 0.5)
        self.snowboy = HotwordDetector(paths,
                                       sensitivity=[sensitivity] * len(paths))
        self.lang = str(lang).lower()
        self.key_phrase = str(key_phrase).lower()

    def found_wake_word(self, frame_data):
        wake_word = self.snowboy.detector.RunDetection(frame_data)
        return wake_word == 1


class HotWordFactory(object):
    CLASSES = {
        "pocketsphinx": PocketsphinxHotWord,
        "snowboy": SnowboyHotWord
    }

    @staticmethod
    def create_hotword(hotword):
        LOG.info("creating " + hotword)
        config = ConfigurationManager.get().get("hot_words", {})
        module = config.get(hotword).get("module")
        clazz = HotWordFactory.CLASSES.get(module)
        return clazz(hotword)

    @staticmethod
    def create_wake_word():
        config = ConfigurationManager.get().get("listener", {})
        wake_word = config.get('wake_word', "hey mycroft").lower()
        LOG.info("creating " + wake_word)
        config = config.get("wake_word_config", {})
        module = config.get('module', "pocketsphinx")
        clazz = HotWordFactory.CLASSES.get(module)
        return clazz(wake_word, config)

    @staticmethod
    def create_standup_word():
        config = ConfigurationManager.get().get("listener", {})
        standup_word = config.get('standup_word', "wake up").lower()
        LOG.info("creating " + standup_word)
        config = config.get("standup_word_config", {})
        module = config.get('module', "pocketsphinx")
        clazz = HotWordFactory.CLASSES.get(module)
        return clazz(standup_word, config)
