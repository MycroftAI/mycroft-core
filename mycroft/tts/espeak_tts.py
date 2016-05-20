import subprocess

from mycroft.tts import TTS, TTSValidator

__author__ = 'seanfitz'

NAME = 'espeak'


class ESpeak(TTS):
    def __init__(self, lang, voice):
        super(ESpeak, self).__init__(lang, voice)

    def execute(self, sentence):
        subprocess.call(['espeak', '-v', self.lang + '+' + self.voice, sentence])


class ESpeakValidator(TTSValidator):
    def __init__(self):
        super(ESpeakValidator, self).__init__()

    def validate_lang(self, lang):
        # TODO
        pass

    def validate_connection(self, tts):
        try:
            subprocess.call(['espeak', '--version'])
        except:
            raise Exception('ESpeak is not installed. Run on terminal: sudo apt-get install espeak')

    def get_instance(self):
        return ESpeak
