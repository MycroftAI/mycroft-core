# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from gtts import gTTS
from gtts.lang import tts_langs

from .tts import TTS, TTSValidator

from mycroft.util.log import LOG

# Live list of languages
# Cached list of supported languages (2020-05-27)
_default_langs = {'af': 'Afrikaans', 'sq': 'Albanian', 'ar': 'Arabic',
                  'hy': 'Armenian', 'bn': 'Bengali', 'bs': 'Bosnian',
                  'ca': 'Catalan', 'hr': 'Croatian', 'cs': 'Czech',
                  'da': 'Danish', 'nl': 'Dutch', 'en': 'English',
                  'eo': 'Esperanto', 'et': 'Estonian', 'tl': 'Filipino',
                  'fi': 'Finnish', 'fr': 'French', 'de': 'German',
                  'el': 'Greek', 'gu': 'Gujarati', 'hi': 'Hindi',
                  'hu': 'Hungarian', 'is': 'Icelandic', 'id': 'Indonesian',
                  'it': 'Italian', 'ja': 'Japanese', 'jw': 'Javanese',
                  'kn': 'Kannada', 'km': 'Khmer', 'ko': 'Korean',
                  'la': 'Latin', 'lv': 'Latvian', 'mk': 'Macedonian',
                  'ml': 'Malayalam', 'mr': 'Marathi',
                  'my': 'Myanmar (Burmese)', 'ne': 'Nepali',
                  'no': 'Norwegian', 'pl': 'Polish', 'pt': 'Portuguese',
                  'ro': 'Romanian', 'ru': 'Russian', 'sr': 'Serbian',
                  'si': 'Sinhala', 'sk': 'Slovak', 'es': 'Spanish',
                  'su': 'Sundanese', 'sw': 'Swahili', 'sv': 'Swedish',
                  'ta': 'Tamil', 'te': 'Telugu', 'th': 'Thai', 'tr': 'Turkish',
                  'uk': 'Ukrainian', 'ur': 'Urdu', 'vi': 'Vietnamese',
                  'cy': 'Welsh', 'zh-cn': 'Chinese (Mandarin/China)',
                  'zh-tw': 'Chinese (Mandarin/Taiwan)',
                  'en-us': 'English (US)', 'en-ca': 'English (Canada)',
                  'en-uk': 'English (UK)', 'en-gb': 'English (UK)',
                  'en-au': 'English (Australia)', 'en-gh': 'English (Ghana)',
                  'en-in': 'English (India)', 'en-ie': 'English (Ireland)',
                  'en-nz': 'English (New Zealand)',
                  'en-ng': 'English (Nigeria)',
                  'en-ph': 'English (Philippines)',
                  'en-za': 'English (South Africa)',
                  'en-tz': 'English (Tanzania)', 'fr-ca': 'French (Canada)',
                  'fr-fr': 'French (France)', 'pt-br': 'Portuguese (Brazil)',
                  'pt-pt': 'Portuguese (Portugal)', 'es-es': 'Spanish (Spain)',
                  'es-us': 'Spanish (United States)'
                  }


_supported_langs = None


def get_supported_langs():
    """Get dict of supported languages.

    Tries to fetch remote list, if that fails a local cache will be used.

    Returns:
        (dict): Lang code to lang name map.
    """
    global _supported_langs
    if not _supported_langs:
        try:
            _supported_langs = tts_langs()
        except Exception:
            LOG.warning('Couldn\'t fetch upto date language codes')
    return _supported_langs or _default_langs


class GoogleTTS(TTS):
    """Interface to google TTS."""
    def __init__(self, lang, config):
        self._google_lang = None
        super(GoogleTTS, self).__init__(lang, config, GoogleTTSValidator(
            self), 'mp3')

    @property
    def google_lang(self):
        """Property containing a converted language code suitable for gTTS."""
        supported_langs = get_supported_langs()
        if not self._google_lang:
            if self.lang.lower() in supported_langs:
                self._google_lang = self.lang.lower()
            elif self.lang[:2].lower() in supported_langs:
                self._google_lang = self.lang[:2]
        return self._google_lang or self.lang.lower()

    def get_tts(self, sentence, wav_file):
        """Fetch tts audio using gTTS.

        Arguments:
            sentence (str): Sentence to generate audio for
            wav_file (str): output file path
        Returns:
            Tuple ((str) written file, None)
        """
        tts = gTTS(text=sentence, lang=self.google_lang)
        tts.save(wav_file)
        return (wav_file, None)  # No phonemes


class GoogleTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(GoogleTTSValidator, self).__init__(tts)

    def validate_lang(self):
        lang = self.tts.google_lang
        if lang.lower() not in get_supported_langs():
            raise ValueError("Language not supported by gTTS: {}".format(lang))

    def validate_connection(self):
        try:
            gTTS(text='Hi').save(self.tts.filename)
        except Exception:
            raise Exception(
                'GoogleTTS server could not be verified. Please check your '
                'internet connection.')

    def get_tts_class(self):
        return GoogleTTS
