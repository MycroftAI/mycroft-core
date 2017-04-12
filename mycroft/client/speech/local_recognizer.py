# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import os
import tempfile
import time
from os.path import join, dirname, abspath

from pocketsphinx import Decoder

__author__ = 'seanfitz, jdorleans'

BASEDIR = dirname(abspath(__file__))


class LocalRecognizer(object):
    decoder=None

    def __init__(self, key_phrase, phonemes, threshold, sample_rate=16000,
                 lang="en-us"):
        self.lang = str(lang)
        self.sample_rate = sample_rate
        self.key_phrase = str(key_phrase)
        self.threshold = threshold
        self.phonemes = phonemes
        self.config=self.create_config()
        LocalRecognizer.decoder = Decoder(self.config)
        LocalRecognizer.decoder.set_keyphrase( 'wake_up', self.key_phrase )
        LocalRecognizer.decoder.set_jsgf_file( 'command', '/home/pma/varios/mycroft/model/es-current.jsgf' )
        LocalRecognizer.decoder.set_search('wake_up')

#    def create_dict(self, key_phrase, phonemes):
#        (fd, file_name) = tempfile.mkstemp()
#        words = key_phrase.split()
#        phoneme_groups = phonemes.split('.')
#        with os.fdopen(fd, 'w') as f:
#            for word, phoneme in zip(words, phoneme_groups):
#                f.write(word + ' ' + phoneme + '\n')
#        return file_name

#    def create_config(self):
#        dict_name = self.create_dict( self.key_phrase, self.phonemes )
#        config = Decoder.default_config()
#        config.set_string('-hmm', join(BASEDIR, 'model', self.lang, 'hmm'))
#        config.set_string('-dict', dict_name)
#        config.set_string('-keyphrase', self.key_phrase)
#        config.set_float('-kws_threshold', self.threshold)
#        config.set_float('-samprate', self.sample_rate)
#        config.set_int('-nfft', 2048)
#        config.set_string('-logfn', '/dev/null')
#        return config

    def create_config(self):
        config = Decoder.default_config()
        config.set_string('-hmm', '/usr/share/pocketsphinx/model/es/es' )
        config.set_string('-dict', '/home/pma/varios/mycroft/model/es.dict' )
        config.set_string('-fdict', '/usr/share/pocketsphinx/model/es/es/noisedict' )
        config.set_string('-featparams', '/usr/share/pocketsphinx/model/es/es/feat.params' )
        config.set_string('-mdef', '/usr/share/pocketsphinx/model/es/es/mdef' )
        config.set_string('-mean', '/usr/share/pocketsphinx/model/es/es/means' )
        config.set_string('-mixw', '/usr/share/pocketsphinx/model/es/es/mixture_weights' )
        config.set_string('-tmat', '/usr/share/pocketsphinx/model/es/es/transition_matrices' )
        config.set_string('-sendump', '/usr/share/pocketsphinx/model/es/es/sendump' )
        config.set_string('-var', '/usr/share/pocketsphinx/model/es/es/variances' )
#        config.set_string('-lm', '/home/pma/varios/mycroft/model/es-current.lm' ) 
#        config.set_string('-jsgf', '/home/pma/varios/mycroft/model/es-current.jsgf' )
        config.set_string('-keyphrase', self.key_phrase)
        config.set_float('-kws_threshold', self.threshold)
        config.set_float('-samprate', self.sample_rate)
        config.set_string('-logfn', 'scripts/logs/decoder.log' )
        return config

    def transcribe(self, byte_data, metrics=None):
        start = time.time()
        LocalRecognizer.decoder.start_utt()
        LocalRecognizer.decoder.process_raw(byte_data, False, False)
        LocalRecognizer.decoder.end_utt()
        if metrics:
            metrics.timer("mycroft.stt.local.time_s", time.time() - start)
        return LocalRecognizer.decoder.hyp()

    def is_recognized(self, byte_data, metrics):
        hyp = self.transcribe(byte_data, metrics)
        return hyp and self.key_phrase in hyp.hypstr.lower()

    def found_wake_word(self, hypothesis):
        return hypothesis and self.key_phrase in hypothesis.hypstr.lower()
