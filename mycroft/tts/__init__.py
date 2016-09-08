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


import logging

import abc
from os.path import dirname, exists, isdir

from mycroft.configuration import ConfigurationManager
from mycroft.tts import espeak_tts
from mycroft.tts import fa_tts
from mycroft.tts import google_tts
from mycroft.tts import mary_tts
from mycroft.tts import mimic_tts
from mycroft.tts import spdsay_tts
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class TTS(object):
    """
    TTS abstract class to be implemented by all TTS engines.

    It aggregates the minimum required parameters and exposes
    ``execute(sentence)`` function.
    """

    def __init__(self, lang, voice, filename='/tmp/tts.wav'):
        super(TTS, self).__init__()
        self.lang = lang
        self.voice = voice
        self.filename = filename

    @abc.abstractmethod
    def execute(self, sentence, client):
        pass


class TTSValidator(object):
    """
    TTS Validator abstract class to be implemented by all TTS engines.

    It exposes and implements ``validate(tts)`` function as a template to
    validate the TTS engines.
    """

    def __init__(self):
        pass

    def validate(self, tts):
        self.__validate_instance(tts)
        self.__validate_filename(tts.filename)
        self.validate_lang(tts.lang)
        self.validate_connection(tts)

    def __validate_instance(self, tts):
        instance = self.get_instance()
        if not isinstance(tts, instance):
            raise AttributeError(
                'tts must be instance of ' + instance.__name__)
        LOGGER.debug('TTS: ' + str(instance))

    def __validate_filename(self, filename):
        if not (filename and filename.endswith('.wav')):
            raise AttributeError(
                'filename: ' + filename + ' must be a .wav file!')
        dir_path = dirname(filename)

        if not (exists(dir_path) and isdir(dir_path)):
            raise AttributeError(
                'filename: ' + filename + ' is not a valid file path!')
        LOGGER.debug('Filename: ' + filename)

    @abc.abstractmethod
    def validate_lang(self, lang):
        pass

    @abc.abstractmethod
    def validate_connection(self, tts):
        pass

    @abc.abstractmethod
    def get_instance(self):
        pass


class TTSFactory(object):
    @staticmethod
    def create():
        """
        Factory method to create a TTS engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tts`` section with
        the name of a TTS module to be read by this method.

        "tts": {
            "module": <engine_name>
        }
        """

        logging.basicConfig()
        config = ConfigurationManager.get().get('tts')
        name = config.get('module')
        lang = config.get(name).get('lang')
        voice = config.get(name).get('voice')

        if name == mimic_tts.NAME:
            tts = mimic_tts.Mimic(lang, voice)
            mimic_tts.MimicValidator().validate(tts)
        elif name == google_tts.NAME:
            tts = google_tts.GoogleTTS(lang, voice)
            google_tts.GoogleTTSValidator().validate(tts)
        elif name == mary_tts.NAME:
            tts = mary_tts.MaryTTS(lang, voice, config[name + '.url'])
            mary_tts.MaryTTSValidator().validate(tts)
        elif name == fa_tts.NAME:
            tts = fa_tts.FATTS(lang, voice, config[name + '.url'])
            fa_tts.FATTSValidator().validate(tts)
        elif name == espeak_tts.NAME:
            tts = espeak_tts.ESpeak(lang, voice)
            espeak_tts.ESpeakValidator().validate(tts)
        else:
            tts = spdsay_tts.SpdSay(lang, voice)
            spdsay_tts.SpdSayValidator().validate(tts)
        return tts
