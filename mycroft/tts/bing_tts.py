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


from mycroft.tts import TTS, TTSValidator

__author__ = 'jarbas'


class BingTTS(TTS):
    def __init__(self, lang, config):
        super(BingTTS, self).__init__(lang, config, BingTTSValidator(
            self))
        self.type = 'wav'
        # pip install git+https://github.com/westparkcom/Python-Bing-TTS.git
        from bingtts import Translator
        api = self.config.get("api_key")
        self.bing = Translator(api)
        self.gender = self.config.get("gender", "male")
        self.format = self.config.get("format", "riff-16khz-16bit-mono-pcm")

    def get_tts(self, sentence, wav_file):
        output = self.bing.speak(sentence, self.lang, self.gender,
                                 self.format)
        with open(wav_file, "w") as f:
            f.write(output)
        return (wav_file, None)  # No phonemes


class BingTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(BingTTSValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        pass

    def get_tts_class(self):
        return BingTTS
