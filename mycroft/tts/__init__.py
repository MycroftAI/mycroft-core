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
import random
from abc import ABCMeta, abstractmethod
from os.path import dirname, exists, isdir

from mycroft.client.enclosure.api import EnclosureAPI
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class TTS(object):
    """
    TTS abstract class to be implemented by all TTS engines.

    It aggregates the minimum required parameters and exposes
    ``execute(sentence)`` function.
    """
    __metaclass__ = ABCMeta

    def __init__(self, lang, voice, validator):
        super(TTS, self).__init__()
        self.lang = lang or 'en-us'
        self.voice = voice
        self.filename = '/tmp/tts.wav'
        self.validator = validator
        self.enclosure = None
        random.seed()

    def init(self, ws):
        self.ws = ws
        self.enclosure = EnclosureAPI(self.ws)

    @abstractmethod
    def execute(self, sentence):
        ''' This performs TTS, blocking until audio completes

        This performs the TTS sequence.  Upon completion, the sentence will
        have been spoken.   Optionally, the TTS engine may have sent visemes
        to the enclosure by the TTS engine.

        Args:
            sentence (str): Words to be spoken
        '''
        # TODO: Move caching support from mimic_tts to here for all TTS
        pass

    def blink(self, rate=1.0):
        if self.enclosure and random.random() < rate:
            self.enclosure.eyes_blink("b")


class TTSValidator(object):
    """
    TTS Validator abstract class to be implemented by all TTS engines.

    It exposes and implements ``validate(tts)`` function as a template to
    validate the TTS engines.
    """
    __metaclass__ = ABCMeta

    def __init__(self, tts):
        self.tts = tts

    def validate(self):
        self.validate_instance()
        self.validate_filename()
        self.validate_lang()
        self.validate_connection()

    def validate_instance(self):
        clazz = self.get_tts_class()
        if not isinstance(self.tts, clazz):
            raise AttributeError('tts must be instance of ' + clazz.__name__)

    def validate_filename(self):
        filename = self.tts.filename
        if not (filename and filename.endswith('.wav')):
            raise AttributeError('file: %s must be in .wav format!' % filename)

        dir_path = dirname(filename)
        if not (exists(dir_path) and isdir(dir_path)):
            raise AttributeError('filename: %s is not valid!' % filename)

    @abstractmethod
    def validate_lang(self):
        pass

    @abstractmethod
    def validate_connection(self):
        pass

    @abstractmethod
    def get_tts_class(self):
        pass


class TTSFactory(object):
    from mycroft.tts.espeak_tts import ESpeak
    from mycroft.tts.fa_tts import FATTS
    from mycroft.tts.google_tts import GoogleTTS
    from mycroft.tts.mary_tts import MaryTTS
    from mycroft.tts.mimic_tts import Mimic
    from mycroft.tts.spdsay_tts import SpdSay

    CLASSES = {
        "mimic": Mimic,
        "google": GoogleTTS,
        "marytts": MaryTTS,
        "fatts": FATTS,
        "espeak": ESpeak,
        "spdsay": SpdSay
    }

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

        from mycroft.tts.remote_tts import RemoteTTS
        config = ConfigurationManager.get().get('tts', {})
        module = config.get('module', 'mimic')
        lang = config.get(module).get('lang')
        voice = config.get(module).get('voice')
        clazz = TTSFactory.CLASSES.get(module)

        if issubclass(clazz, RemoteTTS):
            url = config.get(module).get('url')
            tts = clazz(lang, voice, url)
        else:
            tts = clazz(lang, voice)

        tts.validator.validate()
        return tts
