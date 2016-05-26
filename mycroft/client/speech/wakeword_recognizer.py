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


from mycroft.metrics import Stopwatch

import os
from pocketsphinx import Decoder

from cmath import exp, pi

__author__ = 'seanfitz'

BASEDIR = os.path.dirname(os.path.abspath(__file__))


def fft(x):
    """
    fft function to clean data, but most be converted to array of IEEE floats
    first
    :param x:
    :return:
    """
    N = len(x)
    if N <= 1:
        return x
    even = fft(x[0::2])
    odd = fft(x[1::2])
    T = [exp(-2j*pi*k/N)*odd[k] for k in xrange(N/2)]
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

    sphinx_config.set_string(
        '-hmm', os.path.join(BASEDIR, 'model', lang, 'hmm'))
    sphinx_config.set_string(
        '-dict', os.path.join(BASEDIR, 'model', lang, 'mycroft-en-us.dict'))
    sphinx_config.set_string('-keyphrase', keyphrase)
    sphinx_config.set_float('-kws_threshold', float('1e-45'))
    sphinx_config.set_float('-samprate', samprate)
    sphinx_config.set_int('-nfft', 2048)
    sphinx_config.set_string('-logfn', '/dev/null')

    decoder = Decoder(sphinx_config)

    return Recognizer(decoder)
