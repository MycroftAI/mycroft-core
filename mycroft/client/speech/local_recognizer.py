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


import time

import os
from pocketsphinx.pocketsphinx import Decoder

__author__ = 'seanfitz, jdorleans'

BASEDIR = os.path.dirname(os.path.abspath(__file__))


class LocalRecognizer(object):
    def __init__(self, sample_rate=16000, lang="en-us", key_phrase="mycroft"):
        self.lang = lang
        self.key_phrase = key_phrase
        self.sample_rate = sample_rate
        self.configure()

    def configure(self):
        config = Decoder.default_config()
        config.set_string('-hmm', os.path.join(BASEDIR, 'model', self.lang,
                                               'hmm'))
        config.set_string('-dict', os.path.join(BASEDIR, 'model', self.lang,
                                                'mycroft-en-us.dict'))
        config.set_string('-keyphrase', self.key_phrase)
        config.set_float('-kws_threshold', float('1e-45'))
        config.set_float('-samprate', self.sample_rate)
        config.set_int('-nfft', 2048)
        config.set_string('-logfn', '/dev/null')
        self.decoder = Decoder(config)

    def transcribe(self, byte_data, metrics=None):
        start = time.time()
        self.decoder.start_utt()
        self.decoder.process_raw(byte_data, False, False)
        self.decoder.end_utt()
        if metrics:
            metrics.timer("mycroft.stt.local.time_s", time.time() - start)
        return self.decoder.hyp()

    def is_recognized(self, byte_data, metrics):
        hyp = self.transcribe(byte_data, metrics)
        return hyp and self.key_phrase in hyp.hypstr.lower()

    def found_wake_word(self, hypothesis):
        return hypothesis and self.key_phrase in hypothesis.hypstr.lower()
