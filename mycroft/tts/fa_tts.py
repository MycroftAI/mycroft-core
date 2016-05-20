import json

import requests

from mycroft.tts import TTSValidator
from mycroft.tts.remote_tts import RemoteTTS

__author__ = 'jdorleans'

NAME = 'fatts'


class FATTS(RemoteTTS):
    PARAMS = {
        'voice[name]': 'cmu-slt-hsmm',
        'input[type]': 'TEXT',
        'input[locale]': 'en_US',
        'input[content]': 'Hello World',
        'output[format]': 'WAVE_FILE',
        'output[type]': 'AUDIO'
    }

    def __init__(self, lang, voice, url):
        super(FATTS, self).__init__(lang, voice, url, '/say')

    def build_request_params(self, sentence):
        params = self.PARAMS.copy()
        params['voice[name]'] = self.voice
        params['input[locale]'] = self.lang
        params['input[content]'] = sentence.encode('utf-8')
        return params


class FATTSValidator(TTSValidator):
    def __init__(self):
        super(FATTSValidator, self).__init__()

    def validate_lang(self, lang):
        # TODO
        pass

    def validate_connection(self, tts):
        try:
            resp = requests.get(tts.url + "/info/version", verify=False)
            content = json.loads(resp.content)
            if content['product'].find('FA-TTS') < 0:
                raise Exception('Invalid FA-TTS server.')
        except:
            raise Exception('FA-TTS server could not be verified. Check your connection to the server: ' + tts.url)

    def get_instance(self):
        return FATTS
