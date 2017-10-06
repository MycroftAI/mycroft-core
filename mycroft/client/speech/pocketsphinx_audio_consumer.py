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

from threading import Thread
import wave
import subprocess
from os.path import join, dirname, abspath, exists
import pyaudio
import time
import datetime
import os

import sys

# import pydub
# Copyright 2016 Mycroft AI, Inc.

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.metrics import MetricsAggregator

# from mycroft.util import (
#     get_ipc_directory
# )

from mycroft.util.log import getLogger

from pocketsphinx import Decoder
from mycroft.util import (
    create_signal,
    check_for_signal)

# from mycroft.client.speech.transcribesearch import TranscribeSearch
# import speech_recognition as sr

logger = getLogger(__name__)
__author__ = 'SoloVeniaASaludar'

logger.debug('sys.path =' + str(sys.path))

from pydub.audio_segment import AudioSegment

BASEDIR = dirname(abspath(__file__))
config = ConfigurationManager.get()
listener_config = config.get('listener')
s = config.get('wake_word_ack_cmnd')


class PocketsphinxAudioConsumer(Thread):
# class PocketsphinxAudioConsumer(object):
    """
    PocketsphinxAudioConsumer
    Reads audio and produces utterances
    Based on local pocketsphinx
    """

    # In seconds, the minimum audio size to be sent to remote STT
    MIN_AUDIO_SIZE = 0.5

    def __init__(self, config_listener, lang, emitter):
    # def __init__(self, queue, config_listener, lang, state, wakeup_recognizer, wakeword_recognizer, emitter):
        super(PocketsphinxAudioConsumer, self).__init__()
        # self.SAMPLE_RATE = 44100
        self.SAMPLE_RATE = 16000
        self.SAMPLE_WIDTH = 2
        self.CHUNK = 1024
        self.config = config_listener
        self.lang = lang
        self.emitter = emitter

        # self.energy_threshold = 300  # minimum audio energy to consider for recording
        # self.dynamic_energy_threshold = True
        # self.dynamic_energy_adjustment_damping = 0.15
        # self.dynamic_energy_ratio = 1.5
        # self.pause_threshold = 0.8  # seconds of non-speaking audio before a phrase is considered complete
        # self.phrase_threshold = 0.3  # minimum seconds of speaking audio before we consider the speaking audio a phrase - values below this are ignored (for filtering out clicks and pops)
        # self.non_speaking_duration = 0.5  # seconds of non-speaking audio to keep on both sides of the recording
        # self.multiplier = listener_config.get('multiplier')
        # self.energy_ratio = listener_config.get('energy_ratio')
        # self.mic_level_file = os.path.join(get_ipc_directory(), "mic_level")

        self.audio = pyaudio.PyAudio()

        self.forced_wake = False
        stamp = str(datetime.datetime.now())
        self.record_file = "scripts/logs/mycroft_utterance_%s.wav" % stamp
        # self.record_file = None
        self.wake_word = str(self.config.get(
            'wake_word', "Hey Mycroft")).lower()
        self.phonemes = self.config.get("phonemes", "HH EY . M AY K R AO F T")
        self.num_phonemes = len(self.phonemes.split())
        self.standup_word = str(self.config.get(
            'standup_word', "wake up")).lower()
        self.default_grammar = str(
            self.config.get('grammar', "lm"))
        self.grammar = self.default_grammar

        self.msg_awake = self.config.get('msg_awake', "I'm awake")
        self.msg_not_catch = self.config.get(
            'msg_not_catch', "Sorry, I didn't catch that")
        self.wake_word_ack_cmnd = None
        if s:
            self.wake_word_ack_cmnd = s.split(' ')

        self.metrics = MetricsAggregator()

        model_lang_dir = join(BASEDIR, 'recognizer/model', str(self.lang))
        self.decoder = Decoder(self.create_decoder_config(model_lang_dir))

        self.key_phrase = self.wake_word
        logger.debug("wake_word = " + self.wake_word)
        self.decoder.set_keyphrase('wake_word', self.wake_word)

        jsgf = join(model_lang_dir, 'hello.jsgf')
        if exists(jsgf):
            self.decoder.set_jsgf_file('jsgf', jsgf)
            # self.decoder.set_search('grammar')
        else:
            # lm = join(model_lang_dir, 'en-70k-0.1-pruned.lm')
            # lm = join(model_lang_dir, 'guy6i_like.lm')
            lm = join(model_lang_dir, 'guy6l_like.lm')
            # lm = join(model_lang_dir, 'guy6h_like.lm')
            # lm = join(model_lang_dir, 'en-70k-0.2-pruned.lm')
            # lm = join(model_lang_dir, self.lang + '.lm')
            # lm = join(model_lang_dir, self.lang + '.lm.bin')
            if exists(lm):
                logger.debug("lm = " + lm)
                self.decoder.set_lm_file('lm', str(lm))

        if check_for_signal('skip_wake_word',-1):
        # if listener_config.get('skip_wake_word'):
            self.decoder.set_search('lm')

    def create_decoder_config(self, model_lang_dir):
        decoder_config = Decoder.default_config()
        # hmm_dir = join(model_lang_dir, 'en-us-semi-full')
        # hmm_dir = join(model_lang_dir, 'cmusphinx-en-us-8khz-5.2')
        hmm_dir = join(model_lang_dir, 'cmusphinx-en-us-5.2')
        # hmm_dir = join(model_lang_dir, 'hmm')
        decoder_config.set_string('-hmm', hmm_dir)
        # decoder_config.set_string('-hmm', join(model_lang_dir, hmm_dir))
        # logger.debug("dict = " + model_lang_dir + '/' + self.lang + '.dict')
        if config.get('enclosure', {}).get('platform') == "picroft":
            decoder_config.set_string('-dict',
                                      '/usr/local/lib/python2.7/site-packages/mycroft_core-0.8.20-py2.7.egg/mycroft/client/lspeech/model/en-us/cmudict-en-us_original.dict')
        else:
            decoder_config.set_string('-dict',
                                      '/home/guy/github/mycroft/mycroft-core-mirror/mycroft/client/speech/recognizer/model/en-us/cmudict-en-us_original.dict')
        decoder_config.set_float('-samprate', self.SAMPLE_RATE)
        decoder_config.set_float('-kws_threshold', self.config.get('threshold', 1))
        decoder_config.set_string('-cmninit', '40,3,-1')
        decoder_config.set_string('-logfn', '/tmp/pocketsphinx.log')
        decoder_config.set_string('-keyphrase', self.wake_word)
        return decoder_config

    def wake_word_ack(self):
        if self.wake_word_ack_cmnd:
            subprocess.call(self.wake_word_ack_cmnd)

    def device_name_to_index(self, device_name):
        numdevices = self.audio.get_device_count()
        for device_index in range(0, numdevices):
            device = self.audio.get_device_info_by_index(device_index)
            if device_name == device.get('name'):
                return device_index
        return None


    def transcribe(self, byte_data, metrics=None):
        start = time.time()
        # self.decoder.s
        tsta = self.decoder.start_utt()
        tstb = self.decoder.process_raw(byte_data, False, False)
        tstc = self.decoder.end_utt()
        if metrics:
            metrics.timer("mycroft.stt.local.time_s", time.time() - start)
        hyp = self.decoder.hyp()
        if hyp:
            if self.wake_word in hyp.hypstr.lower() or check_for_signal('skip_wake_word',-1):
            # if self.wake_word in hyp.hypstr.lower() or listener_config.get('skip_wake_word'):
                logger.debug("transcribe get kw search = " + self.decoder.get_search())
                self.decoder.set_search('lm')
            else:
                self.decoder.set_keyphrase('wake_word', self.wake_word)
                self.decoder.set_search('_default')
            # logger.debug("transcribe search = " + self.decoder.get_search())
            logger.debug("transcribe hyp.hypstr = " + hyp.hypstr)
            # logger.debug("transcribe success! decoder rtn = " + str(tstb))
            # logger.debug("transcribe success, Byte_data = " + str(len(byte_data)))
        # else:
        #     logger.debug("transcribe search = " + self.decoder.get_search())
        #     logger.debug("transcribe hyp = " + str(hyp))
        #     logger.debug("transcribe failed, decoder rtn = " + str(tstb))
        #     logger.debug("transcribe failed, Byte_data = " + str(len(byte_data)))
        return hyp

    def found_wake_word(self, frame_data):
        hyp = self.transcribe(frame_data)
        if hyp:
            logger.debug("found_wake_word hyp.hypstr = " + hyp.hypstr)

        return hyp and self.wake_word in hyp.hypstr.lower()

    def __speak(self, utterance):
        payload = {
            'utterance': utterance,
            'session': self.session
        }
        self.emitter.emit("speak", Message("speak", payload))
