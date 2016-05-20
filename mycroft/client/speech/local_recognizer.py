import time

import os
from pocketsphinx.pocketsphinx import *

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
        config.set_string('-hmm', os.path.join(BASEDIR, 'model', self.lang, 'hmm'))
        config.set_string('-dict', os.path.join(BASEDIR, 'model', self.lang, 'mycroft-en-us.dict'))
        config.set_string('-keyphrase', self.key_phrase)
        config.set_float('-kws_threshold', float('1e-45'))
        config.set_float('-samprate', self.sample_rate)
        config.set_int('-nfft', 2048)
        config.set_string('-logfn', '/dev/null')
        self.decoder = Decoder(config)

    def transcribe(self, wav_data, metrics=None):
        start = time.time()
        self.decoder.start_utt()
        self.decoder.process_raw(wav_data, False, False)
        self.decoder.end_utt()
        if metrics:
            metrics.timer("mycroft.stt.local.time_s", time.time() - start)
        return self.decoder.hyp()
