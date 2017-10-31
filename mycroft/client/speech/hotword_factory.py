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
import tempfile
import time

import os
from os.path import dirname, exists, join, abspath

from mycroft.configuration import Configuration
from mycroft.util.log import LOG
from mycroft.client.speech.transcribesearch import TranscribeSearch

from mycroft.util import (
    create_signal,
    check_for_signal)

RECOGNIZER_DIR = join(abspath(dirname(__file__)), "recognizer")


class HotWordEngine(object):
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        self.lang = str(lang).lower()
        self.key_phrase = str(key_phrase).lower()
        # rough estimate 1 phoneme per 2 chars
        self.num_phonemes = len(key_phrase) / 2 + 1
        if config is None:
            config = Configuration.get().get("hot_words", {})
            config = config.get(self.key_phrase, {})
        self.config = config
        self.listener_config = Configuration.get().get("listener", {})

    def found_wake_word(self, frame_data):
        return False


class PocketsphinxHotWord(HotWordEngine):
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        super(PocketsphinxHotWord, self).__init__(key_phrase, config, lang)
        # Hotword module imports
        from pocketsphinx import Decoder
        # Hotword module config
        module = self.config.get("module")
        if module != "pocketsphinx":
            LOG.warning(
                str(module) + " module does not match with "
                              "Hotword class pocketsphinx")
        # Hotword module params
        self.mww = self.config.get("mww")
        self.mww_no_skills = self.config.get("mww_no_skills")
        model_file = join(RECOGNIZER_DIR, 'model', self.lang)
        LOG.debug(" model_file 1 = " + str(model_file))
        if self.mww:
            LOG.debug(" mww 1 = "+str(self.mww))
            LOG.debug(" join(model_file,self.config.get('phonemes', '')) = " +
                      join(model_file, self.config.get("phonemes", "")))
            dict_name = join(model_file, self.config.get("phonemes", ""))
        else:
            LOG.debug(" mww 2 = "+str(self.mww))
            dict_name = self.create_dict(
                key_phrase,
                self.config.get("phonemes", "HH EY . M AY K R AO F T")
            )
            # dict_name = self.create_dict(key_phrase, self.phonemes)
            self.phonemes = self.config.get(
                "phonemes",
                "HH EY . M AY K R AO F T"
            )
            self.num_phonemes = len(self.phonemes.split())

        self.threshold = self.config.get("threshold", 1e-90)
        self.sample_rate = self.listener_config.get("sample_rate", 16000)
        config = self.create_config(dict_name, Decoder.default_config())
        self.decoder = Decoder(config)

        if self.mww:
            self.decoder.set_kws('brands', str(join(model_file, key_phrase)))
            self.decoder.set_search('brands')

        self.accum_text = ''
        self.accum_audio = ''
        self.transcribe_start = time.time()

    def create_dict(self, key_phrase, phonemes):
        (fd, file_name) = tempfile.mkstemp()
        words = key_phrase.split()
        phoneme_groups = phonemes.split('.')
        with os.fdopen(fd, 'w') as f:
            for word, phoneme in zip(words, phoneme_groups):
                f.write(word + ' ' + phoneme + '\n')
        return file_name

    def create_config(self, dict_name, config):
        model_file = join(RECOGNIZER_DIR, 'model', self.lang, 'hmm')
        if not exists(model_file):
            LOG.error('PocketSphinx model not found at ' + str(model_file))

        if not self.mww:
            config.set_string('-keyphrase', self.key_phrase)
            LOG.debug(" mww 4 = "+str(self.mww))

        config.set_string('-hmm', model_file)
        config.set_string('-dict', str(dict_name))
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

        if self.mww:
            if hyp:
                if hyp.hypstr.lower() > '':

                    if time.time() - self.transcribe_start > 2:
                        LOG.debug(
                            "time.time() - self.transcribe_start = " +
                            str(time.time() - self.transcribe_start))
                        LOG.debug("accum_text 1 = "+self.accum_text)
                        TranscribeSearch()\
                            .write_transcribed_files(
                            self.accum_audio, self.accum_text
                        )
                        self.accum_text = hyp.hypstr.lower()
                        self.accum_audio = frame_data
                        self.transcribe_start = time.time()
                    else:
                        LOG.debug(
                            "2 time.time() - self.transcribe_start = " +
                            str(time.time() - self.transcribe_start))
                        self.accum_text += hyp.hypstr.lower()
                        self.accum_audio += frame_data
                        self.transcribe_start = time.time()
                        LOG.debug("accum_text 2 = "+self.accum_text)

                return hyp
        else:
            return hyp and self.key_phrase in hyp.hypstr.lower()


class SnowboyHotWord(HotWordEngine):
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        super(SnowboyHotWord, self).__init__(key_phrase, config, lang)
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
        return wake_word == 1


class HotWordFactory(object):
    CLASSES = {
        "pocketsphinx": PocketsphinxHotWord,
        "snowboy": SnowboyHotWord
    }

    @staticmethod
    def create_hotword(hotword="hey mycroft", config=None, lang="en-us"):
        LOG.info("creating " + hotword)
        if not config:
            config = Configuration.get().get("hotwords", {})
        module = config.get(hotword).get("module", "pocketsphinx")
        config = config.get(hotword, {"module": module})
        clazz = HotWordFactory.CLASSES.get(module)
        try:
            return clazz(hotword, config, lang=lang)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            LOG.exception('Could not create hotword. Falling back to default.')
            return HotWordFactory.CLASSES['pocketsphinx']()
