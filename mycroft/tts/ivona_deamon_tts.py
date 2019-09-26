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

# CONFIGURATION EXAMPLE
#   "tts": {
#       "module": "ivonaDeamon",
#       "ivonaDeamon": {
#         "deamon_host": "127.0.0.1",
#         "deamon_port": 9123,
#       }
#   }

import socket
import wave
import sys
import subprocess

from mycroft.tts import TTS, TTSValidator
from mycroft.util import LOG
from mycroft.configuration import Configuration


class IvonaTTSDeamon(TTS):
    socketConnection = ''

    def __init__(self, lang, config):
        super(IvonaTTSDeamon, self).\
            __init__(lang, config, IvonaValidator(self))

    def get_tts(self, sentence, wav_file):
        self.connectToSocket()
        s = self.socketConnection
        s.sendall(sentence.encode('utf-8'))
        s.sendall(b'\x00')
        sampleRate = 8000.0  # hertz
        wavObj = wave.open(wav_file, "w")
        wavObj.setnchannels(1)  # mono
        wavObj.setsampwidth(2)
        wavObj.setframerate(sampleRate)
        while 1:
            chunk = s.recv(500000)
            if chunk == b'':
                break
            wavObj.writeframesraw(chunk)
        wavObj.close()
        s.close()
        return (wav_file, None)  # No phonemes

    def connectToSocket(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            LOG.warning("Socket successfully created")
        except socket.error as err:
            LOG.warning("socket creation failed with error %s" % (err))

        config = Configuration.get().get("tts").get("ivonaDeamon")
        HOST = config.get("deamon_host", "")
        PORT = config.get("deamon_port", "")

        s.connect((HOST, PORT))
        self.socketConnection = s


class IvonaValidator(TTSValidator):
    def __init__(self, tts):
        super(IvonaValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            config = Configuration.get().get("tts").get("ivonaDeamon")
            HOST = config.get("deamon_host", "")
            PORT = config.get("deamon_port", "")

            s.connect((HOST, PORT))
        except Exception:
            raise Exception(
                'there is no Ivona deamon')

    def get_tts_class(self):
        return IvonaTTSDeamon
