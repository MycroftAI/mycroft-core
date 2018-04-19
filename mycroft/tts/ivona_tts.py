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
        self.type = 'mp3'
        self.engine = pyvona.create_voice(self.access_key, self.secret_key)
        self.engine.codec = 'mp3'
        if self.gender == 'female':
            self.engine.voice_name = 'Salli'
        else:
            self.engine.voice_name = 'Joey'

    def get_tts(self, sentence, file_name):
        self.engine.fetch_voice(sentence, file_name)


class IvonaValidator(TTSValidator):
    def __init__(self, tts):
        super(IvonaValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            with tempfile.TemporaryFile(suffix='.mp3') as f:
                self.tts.engine.fetch_voice_fp('test', f)
        except Exception:
            raise Exception(
                'pyvona is not installed')

    def get_tts_class(self):
        return Ivona
