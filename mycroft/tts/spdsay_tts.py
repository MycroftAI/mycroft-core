import subprocess

from mycroft.tts import TTS, TTSValidator

__author__ = 'jdorleans'

NAME = 'spdsay'


class SpdSay(TTS):
    def __init__(self, lang, voice):
        super(SpdSay, self).__init__(lang, voice)

    def execute(self, sentence):
        subprocess.call(
            ['spd-say', '-l', self.lang, '-t', self.voice, sentence])


class SpdSayValidator(TTSValidator):
    def __init__(self):
        super(SpdSayValidator, self).__init__()

    def validate_lang(self, lang):
        # TODO
        pass

    def validate_connection(self, tts):
        try:
            subprocess.call(['spd-say', '--version'])
        except:
            raise Exception(
                'SpdSay is not installed. Run on terminal: sudo apt-get'
                'install speech-dispatcher')

    def get_instance(self):
        return SpdSay
