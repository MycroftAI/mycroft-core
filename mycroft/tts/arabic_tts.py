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
import os
import stat
import subprocess
from threading import Thread
from time import time, sleep

import os.path
from os.path import exists, join, expanduser

from mycroft import MYCROFT_ROOT_PATH
from mycroft.api import DeviceApi
from mycroft.configuration import Configuration
from mycroft.tts import TTS, TTSValidator
from mycroft.util.download import download
from mycroft.util.log import LOG

config = Configuration.get().get("tts").get("arabic")

BIN = './tts.sh'
PATH = config.get("path")
VOICE = config.get("voice")
DIAC = config.get("diac")
VOL = config.get("vol")
SPEED = config.get("speed")

class ArabicTTS(TTS):
    def __init__(self, lang, config):
        super(ArabicTTS, self).__init__(
            lang, config, ArabicTTSValidator(self), 'wav'
        )
        self.dl = None
        self.clear_cache()

    @property
    def args(self):
        """ Build ArabicTTS arguments. """
        args = [BIN, '-v', VOICE, '-d', DIAC, '-vol', VOL, '-s', SPEED]
        return args

    def get_tts(self, sentence, wav_file):
        #  Generate WAV and phonemes
        phonemes = subprocess.check_output(self.args + ['-o', wav_file,
                                                        '-i', sentence], cwd=PATH)
        return wav_file, phonemes


class ArabicTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(ArabicTTSValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO: Verify version of flite can handle the requested language
        pass

    def validate_connection(self):
        try:
            subprocess.call([PATH+'/'+BIN])
        except:
            LOG.info("Failed to find " + BIN + " at: " + PATH)
            raise Exception(
                'ArabicTTS was not found.')

    def get_tts_class(self):
        return ArabicTTS
