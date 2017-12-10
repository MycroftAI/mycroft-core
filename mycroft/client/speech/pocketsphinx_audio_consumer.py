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

from threading import Thread
import subprocess
from os.path import join, dirname, abspath, exists
import pyaudio
import time
import datetime

import sys

# import pydub
# Copyright 2016 Mycroft AI, Inc.

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.metrics import MetricsAggregator

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

# from pydub.audio_segment import AudioSegment

BASEDIR = dirname(abspath(__file__))
config = ConfigurationManager.get()
listener_config = config.get('listener')
s = config.get('wake_word_ack_cmnd')


# class PocketsphinxAudioConsumer(multiprocessing.Process):
class PocketsphinxAudioConsumer(Thread):
    """
    PocketsphinxAudioConsumer
    Reads audio and produces utterances
    Based on local pocketsphinx
    """

    # In seconds, the minimum audio size to be sent to remote STT
    MIN_AUDIO_SIZE = 0.5

    def __init__(self, config_listener, lang, emitter):
        super(PocketsphinxAudioConsumer, self).__init__()
        # self.SAMPLE_RATE = 44100
        self.SAMPLE_RATE = 16000
        self.SAMPLE_WIDTH = 2
        self.CHUNK = 1024
        self.config = config_listener
        self.lang = lang
        self.emitter = emitter

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
            self.decoder.set_search('grammar')
            self.decoder.set_jsgf_file('jsgf', str(jsgf))
        else:
            # lm = join(model_lang_dir, 'en-70k-0.1-pruned.lm')
            # lm = join(model_lang_dir, 'guy6i_like.lm')
            lm = join(model_lang_dir, 'local_stt_example_language_model.lm')
            # lm = join(model_lang_dir, 'guy6h_like.lm')
            # lm = join(model_lang_dir, 'en-70k-0.2-pruned.lm')
            # lm = join(model_lang_dir, self.lang + '.lm')
            # lm = join(model_lang_dir, self.lang + '.lm.bin')
            if exists(lm):
                logger.debug("lm = " + lm)
                self.decoder.set_lm_file('lm', str(lm))

        if check_for_signal('skip_wake_word', -1):
            self.decoder.set_search('lm')
        elif listener_config.get('skip_wake_word', True) and \
                not check_for_signal('restartedFromSkill', 10):
            self.decoder.set_search('lm')
            create_signal('skip_wake_word')

    def create_decoder_config(self, model_lang_dir):
        decoder_config = Decoder.default_config()
        # hmm_dir = join(model_lang_dir, 'en-us-semi-full')
        # hmm_dir = join(model_lang_dir, 'cmusphinx-en-us-8khz-5.2')
        # hmm_dir = join(model_lang_dir, 'cmusphinx-en-us-5.2')

        hmm_dir = join(model_lang_dir, 'hmm')
        decoder_config.set_string('-hmm', hmm_dir)
        decoder_config.set_string('-dict',
                                  BASEDIR +
                                  '/recognizer/model/en-us/'
                                  'cmudict-en-us.dict'
                                  )

        decoder_config.set_float('-samprate', self.SAMPLE_RATE)
        decoder_config.set_float('-kws_threshold',
                                 self.config.get('threshold', 1))
        decoder_config.set_string('-cmninit', '40,3,-1')
        decoder_config.set_string('-logfn', '/dev/null')
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
        # logger.debug("Thinking...")
        # logger.debug("start utt time.time() = " + str(time.time()))
        self.decoder.start_utt()
        # logger.debug("1 start process_raw time.time() = " + str(time.time()))
        self.decoder.process_raw(byte_data, False, False)
        # logger.debug("2 start end_utt time.time() = " + str(time.time()))
        self.decoder.end_utt()
        if metrics:
            metrics.timer("mycroft.stt.local.time_s", time.time() - start)
        # logger.debug("transcribing start = " + str(time.time() - start))
        hyp = self.decoder.hyp()
        # logger.debug("end hyp() time.time() = " + str(time.time()))
        # logger.debug("*******************************")
        # logger.debug("Local transcribing end: total time = " +
        #              str(time.time() - start))
        # logger.debug("*******************************")
        if hyp:
            logger.debug("*******************************")
            logger.debug("Local transcribing end: total time = " +
                         str(time.time() - start))
            logger.debug("*******************************")
            if self.wake_word in hyp.hypstr.lower() or \
                    check_for_signal('skip_wake_word', -1):
                self.decoder.set_search('lm')
            else:
                self.decoder.set_keyphrase('wake_word', self.wake_word)
                self.decoder.set_search('_default')
            # logger.debug("transcribe search = " + self.decoder.get_search())
            logger.debug("*******************************")
            logger.debug("transcribe hyp.hypstr = " + hyp.hypstr)
            logger.debug("*******************************")
        return hyp

    def found_wake_word(self, frame_data):
        hyp = self.transcribe(frame_data)
        if hyp and self.wake_word in hyp.hypstr.lower():
            logger.debug("found_wake_word hyp.hypstr = " + hyp.hypstr)

        if check_for_signal('skip_wake_word', -1):
            return bool(hyp.hypstr > '')
        else:
            return hyp and self.wake_word in hyp.hypstr.lower()

    def __speak(self, utterance):
        payload = {
            'utterance': utterance,
            'session': self.session
        }
        self.emitter.emit("speak", Message("speak", payload))
