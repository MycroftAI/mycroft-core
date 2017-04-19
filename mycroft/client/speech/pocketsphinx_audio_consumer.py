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
from os.path import join, dirname, abspath, exists

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.metrics import MetricsAggregator
from mycroft.session import SessionManager
from mycroft.util import check_for_signal
from mycroft.util.log import getLogger

from pocketsphinx import Decoder

logger = getLogger(__name__)
__author__ = 'SoloVeniaASaludar'

BASEDIR = dirname(abspath(__file__))


class PocketsphinxAudioConsumer(Thread):
    """
    PocketsphinxAudioConsumer
    Reads audio and produces utterances
    Based on local pocketsphinx
    """

    # In seconds, the minimum audio size to be sent to remote STT
    MIN_AUDIO_SIZE = 0.5

    def __init__(self, config_listener, lang, state, emitter, source):
        super(PocketsphinxAudioConsumer, self).__init__()
        self.config_listener = config_listener
        self.lang = lang
        self.state = state
        self.emitter = emitter
        self.source = source

        self.forced_wake = False
        self.record_file = None
        self.wake_word = str(self.config_listener.get(
             'wake_word', "Hey Mycroft")).lower()
        self.standup_word = str(self.config_listener.get(
             'standup_word', "wake up")).lower()
        self.default_grammar = str(
             self.config_listener.get('grammar', "lm"))
        self.grammar = self.default_grammar

        self.msg_awake = self.config_listener.get('msg_awake', "I'm awake")
        self.msg_not_catch = self.config_listener.get(
             'msg_not_catch', "Sorry, I didn't catch that")

        self.metrics = MetricsAggregator()

        model_lang_dir = join(BASEDIR, 'model', str(self.lang))
        self.decoder = Decoder(self.create_decoder_config(model_lang_dir))
        self.decoder.set_keyphrase('wake_word', self.wake_word)
        jsgf = join(model_lang_dir, 'es.jsgf')
        if exists(jsgf):
            self.decoder.set_jsgf_file('jsgf', jsgf)
        lm = join(model_lang_dir, 'es.lm')
        if exists(lm):
            self.decoder.set_lm_file('lm', lm)

    def run(self):
        with self.source:  # open audio
            while self.state.running:
                # start new session
                SessionManager.touch()
                self.session = SessionManager.get().session_id

                wake_word_found = self.wait_until_wake_word()
                if wake_word_found:
                    logger.debug("wake_word detected.")

                    payload = {
                        'utterance': self.wake_word,
                        'session': self.session
                    }
                    context = {'session': self.session}
                    self.emitter.emit("recognizer_loop:wakeword",
                                      payload, context)

                context = {'session': self.session}
                self.emitter.emit("recognizer_loop:record_begin", context)
                audio, text = self.record_phrase()
                self.emitter.emit("recognizer_loop:record_end", context)
                logger.debug("recorded.")

                if self.state.sleeping:
                    self.standup(text)
                else:
                    self.process(audio, text)

    def standup(self, text):
        if text and self.standup_word in text:
            SessionManager.touch()
            self.state.sleeping = False
            self.__speak(self.msg_awake)
            self.metrics.increment("mycroft.wakeup")

    def process(self, audio, text):

        # save this record in file if requested
        if self.record_file:
            wav_name = self.record_file
            waveFile = wave.open(self.record_file, 'wb')
            self.record_file = None
            waveFile.setnchannels(1)
            waveFile.setsampwidth(self.source.SAMPLE_WIDTH)
            waveFile.setframerate(self.source.SAMPLE_RATE)
            waveFile.writeframes(audio)
            waveFile.close()

        if not self.grammar:
            # do not translate if only record is requested
            # recover default mode
            self.grammar = self.default_grammar
        elif text:
            # already translated in local recognizer
            payload = {
                'utterances': [text],
                'lang': self.lang,
            }
            context = {'session': self.session}
            self.emitter.emit("recognizer_loop:utterance", payload, context)
            self.metrics.attr('utterances', [text])
        else:
            logger.error("Speech Recognition could not understand audio")
            self.__speak(self.msg_not_catch)

    def __speak(self, utterance):
        payload = {
            'utterance': utterance,
            'session': self.session
        }
        self.emitter.emit("speak", Message("speak", payload))

    #
    # ResponsiveRecognizer
    #

    # The maximum audio in seconds to keep for transcribing a phrase
    # The wake word must fit in this time
    SAVED_WW_SEC = 1.0

    # The maximum length a phrase can be recorded,
    # provided there is noise the entire time
    RECORDING_TIMEOUT = 10.0

    # Time between pocketsphinx checks for the wake word
    SEC_BETWEEN_WW_CHECKS = 0.2

    def create_decoder_config(self, model_lang_dir):
        decoder_config = Decoder.default_config()
        hmm_dir = join(model_lang_dir, 'hmm')
        decoder_config.set_string('-hmm', join(model_lang_dir, hmm_dir))
        decoder_config.set_string('-dict', join(model_lang_dir, 'es.dict'))
        decoder_config.set_float('-samprate', self.source.SAMPLE_RATE)
        decoder_config.set_string('-logfn', 'scripts/logs/decoder.log')
        return decoder_config

    def record_sound_chunk(self):
        # return self.source.stream.read(self.source.CHUNK)
        # TODO: if muted
        return self.source.stream.wrapped_stream.read(self.source.CHUNK)

    def record_phrase(self):
        logger.debug("Waiting for command[%s]...", self.grammar)
        sec_per_buffer = float(self.source.CHUNK) / self.source.SAMPLE_RATE

        # Maximum number of chunks to record before timing out
        max_chunks = int(self.RECORDING_TIMEOUT / sec_per_buffer)

        # bytearray to store audio in
        byte_data = ""

        num_chunks = 0
        in_speech = False
        hypstr = None
        if self.grammar:
            self.decoder.set_search(self.grammar)
        utt_running = False

        self.source.stream.wrapped_stream.start_stream()

        while num_chunks < max_chunks:
            chunk = self.record_sound_chunk()
            byte_data += chunk
            num_chunks += 1

            if not self.grammar:
                # no stt, only record
                continue

            if not utt_running:
                self.decoder.start_utt()
                utt_running = True

            self.decoder.process_raw(chunk, False, False)

            if self.decoder.get_in_speech():
                # voice
                in_speech = True
            elif in_speech:
                # silence
                # voice->silence
                logger.debug("voice->silence")
                in_speech = False

                self.decoder.end_utt()
                utt_running = False

                hyp = self.decoder.hyp()
                if hyp and hyp.hypstr:
                    hypstr = hyp.hypstr
                    logger.debug("hyp=%s", hypstr)
                    break
                logger.debug("false speech, discarded")

        if utt_running:
            self.decoder.end_utt()
            utt_running = False

        self.source.stream.wrapped_stream.stop_stream()

        return (byte_data, hypstr)

    def wait_until_wake_word(self):
        # bytearray to store audio in
        byte_data = ""

        sec_per_buffer = float(self.source.CHUNK) / self.source.SAMPLE_RATE
        buffers_per_check = self.SEC_BETWEEN_WW_CHECKS / sec_per_buffer
        buffers_since_check = 0.0

        # Max bytes for byte_data before audio is removed from the front
        max_size = self.SAVED_WW_SEC * self.source.SAMPLE_RATE

        self.decoder.set_search('wake_word')

        in_speech = False
        utt_running = False
        self.source.stream.wrapped_stream.start_stream()

        logger.debug("Waiting for wake word...")
        wake_word_found = False
        while not wake_word_found:
            if self.forced_wake or check_for_signal('buttonPress'):
                logger.debug("Forced wake word...")
                self.forced_wake = False
                break

            chunk = self.record_sound_chunk()

            if len(byte_data) < max_size:
                byte_data += chunk
            else:  # Remove beginning of audio and add new chunk to end
                byte_data = byte_data[len(chunk):] + chunk

            buffers_since_check += 1.0
            if buffers_since_check > buffers_per_check:
                buffers_since_check -= buffers_per_check

                if not utt_running:
                    self.decoder.start_utt()
                    utt_running = True

                self.decoder.process_raw(byte_data, False, False)

                if self.decoder.get_in_speech():
                    # voice
                    in_speech = True
                elif in_speech:
                    # voice->silence
                    logger.debug("silence->speech")
                    in_speech = False

                    self.decoder.end_utt()
                    utt_running = False

                    hyp = self.decoder.hyp()
                    if hyp:
                        logger.debug("hypstr=%s", hyp.hypstr)
                        wake_word_found = (self.wake_word in hyp.hypstr)

        if utt_running:
            self.decoder.end_utt()

        self.source.stream.wrapped_stream.stop_stream()

        return wake_word_found

    def record(self, msg):
        self.forced_wake = True
        self.record_file = msg.data.get("record_filename")
        self.grammar = msg.data.get("grammar", self.default_grammar)
        self.session = msg.context.get("session")
