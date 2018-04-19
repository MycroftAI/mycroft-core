from mycroft.configuration import Configuration
from mycroft.tts import TTS, TTSValidator
import pyvona


class Ivona(TTS):
    def __init__(self, lang, config):
        super(Ivona, self).__init__(lang, config, IvonaValidator(self))
        self.config = Configuration.get().get("tts", {}).get("ivona", {})
        self.access_key = self.config.get("access_key")
        self.secret_key = self.config.get("secret_key")
        self.gender = self.config.get("gender")
        self.engine = pyvona.create_voice(self.access_key, self.secret_key)
        if self.gender == 'female':
            self.engine.voice_name = 'Salli'
        else:
            self.engine.voice_name = 'Joey'

    def execute(self, sentence, ident=None):
        self.begin_audio()
        self.engine.speak(sentence)
        self.end_audio()


class IvonaValidator(TTSValidator):
    def __init__(self, tts):
        super(IvonaValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            self.engine.speak(sentence)
        except:
            raise Exception(
                'ESpeak is not installed. Run: sudo apt-get install espeak')

    def get_tts_class(self):
        return Ivona
