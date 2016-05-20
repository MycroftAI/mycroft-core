import subprocess
from os.path import join

from mycroft import MYCROFT_ROOT_PATH
from mycroft.tts import TTS, TTSValidator
from mycroft.configuration.config import ConfigurationManager

__author__ = 'jdorleans'

config = ConfigurationManager.get_config().get("tts", {})

NAME = 'mimic'
BIN = config.get("mimic.path", join(MYCROFT_ROOT_PATH, 'mimic', 'bin', 'mimic'))


class Mimic(TTS):
    def __init__(self, lang, voice):
        super(Mimic, self).__init__(lang, voice)

    def execute(self, sentence):
        subprocess.call([BIN, '-voice', self.voice, '-t', sentence])


class MimicValidator(TTSValidator):
    def __init__(self):
        super(MimicValidator, self).__init__()

    def validate_lang(self, lang):
        pass

    def validate_connection(self, tts):
        try:
            subprocess.call([BIN, '--version'])
        except:
            raise Exception('Mimic is not installed. Make sure install-mimic.sh ran properly.')

    def get_instance(self):
        return Mimic
