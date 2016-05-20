from mycroft.metrics import Stopwatch

__author__ = 'seanfitz'
import os
import sys

from pocketsphinx import *


BASEDIR = os.path.dirname(os.path.abspath(__file__))


from cmath import exp, pi

def fft(x):
    """
    fft function to clean data, but most be converted to array of IEEE floats first
    :param x:
    :return:
    """
    N = len(x)
    if N <= 1: return x
    even = fft(x[0::2])
    odd =  fft(x[1::2])
    T= [exp(-2j*pi*k/N)*odd[k] for k in xrange(N/2)]
    return [even[k] + T[k] for k in xrange(N/2)] + \
           [even[k] - T[k] for k in xrange(N/2)]


class Recognizer(object):
    def __init__(self, local_recognizer):
        self.local_recognizer = local_recognizer

    def transcribe(self, wav_data, metrics=None):
        timer = Stopwatch()
        timer.start()
        self.local_recognizer.start_utt()
        self.local_recognizer.process_raw(wav_data, False, False)
        self.local_recognizer.end_utt()
        if metrics:
            metrics.timer("mycroft.stt.local.time_s", timer.stop())
        return self.local_recognizer.hyp()


def create_recognizer(samprate=16000, lang="en-us", keyphrase="hey mycroft"):
    sphinx_config = Decoder.default_config()

    sphinx_config.set_string('-hmm', os.path.join(BASEDIR, 'model', lang, 'hmm'))
    sphinx_config.set_string('-dict', os.path.join(BASEDIR, 'model', lang, 'mycroft-en-us.dict'))
    sphinx_config.set_string('-keyphrase', keyphrase)
    sphinx_config.set_float('-kws_threshold', float('1e-45'))
    sphinx_config.set_float('-samprate', samprate)
    sphinx_config.set_int('-nfft', 2048)
    sphinx_config.set_string('-logfn', '/dev/null')

    decoder = Decoder(sphinx_config)

    return Recognizer(decoder)