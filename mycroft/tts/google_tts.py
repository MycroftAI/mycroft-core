from gtts import gTTS

from mycroft.tts import TTS, TTSValidator
from mycroft.util import play_wav

__author__ = 'jdorleans'

NAME = 'gtts'


class GoogleTTS(TTS):
    def __init__(self, lang, voice):
        super(GoogleTTS, self).__init__(lang, voice)

    def execute(self, sentence):
        tts = gTTS(text=sentence, lang=self.lang)
        tts.save(self.filename)
        play_wav(self.filename)


class GoogleTTSValidator(TTSValidator):
    def __init__(self):
        super(GoogleTTSValidator, self).__init__()

    def validate_lang(self, lang):
        # TODO
        pass

    def validate_connection(self, tts):
        try:
            gTTS(text='Hi').save(tts.filename)
        except:
            raise Exception(
                'GoogleTTS server could not be verified. Please check your '
                'internet connection.')

    def get_instance(self):
        return GoogleTTS
