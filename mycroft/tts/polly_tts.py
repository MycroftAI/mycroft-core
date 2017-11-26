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
import hashlib
import os
import os.path
from contextlib import closing
from tempfile import gettempdir

from mycroft.tts import TTS, TTSValidator
from mycroft.configuration import Configuration
from mycroft.util.log import LOG


class PollyTTS(TTS):
    def __init__(self, lang, voice):
        super(PollyTTS, self).__init__(lang, voice, PollyTTSValidator(self))
        from boto3 import Session
        # FS cache
        self.type = "mp3"
        self.config = Configuration.get().get("tts", {}).get("polly", {})
        self.cache = self.config.get("cache", True)
        self.key_id = self.config.get("key_id", '')
        self.key = self.config.get("secret_key", '')
        self.region = self.config.get("region", 'us-west-2')
        session = Session(aws_access_key_id=self.key_id,
                          aws_secret_access_key=self.key,
                          region_name=self.region)
        self.polly = session.client('polly')

    def get_tts(self, sentence, wav_file):
        wav_file = self.retrieve_audio(sentence)
        return (wav_file, None)  # No phonemes

    def describe_voices(self, language_code):
        # example 'it-IT' useful to retrieve voices
        return self.polly.describe_voices(LanguageCode=language_code)

    def calculate_hash(self, data):
        m = hashlib.md5()
        m.update(data)
        return m.hexdigest()

    def retrieve_audio(self, sentence):
        output_format = 'mp3'
        hash = self.calculate_hash('{0}-{1}'.format(self.voice, sentence))
        file_name = '{0}.{1}'.format(hash, output_format)
        output = os.path.join(gettempdir(), file_name)

        if self.cache and os.path.isfile(output):
            LOG.info('Using file {0}'.format(output))
            return output

        # call AWS
        try:
            response = self.polly.synthesize_speech(Text=sentence,
                                                    OutputFormat=output_format,
                                                    VoiceId=self.voice)
        except Exception as err:
            LOG.error(err)
            return None

        # access the audio stream from the response
        if 'AudioStream' in response:
            with closing(response['AudioStream']) as stream:
                try:
                    # open a file for writing the output as a binary stream
                    with open(output, 'wb') as file:
                        file.write(stream.read())
                        LOG.info('Generated new file {0}'.format(output))
                        return output
                except IOError as error:
                    LOG.error(error)
                    return None
        LOG.error('No AudioStream in response')
        return None


class PollyTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(PollyTTSValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_dependencies(self):
        try:
            from boto3 import Session
        except ImportError:
            raise Exception(
                'PollyTTS dependencies not installed, please run pip install '
                'boto3 ')

    def validate_connection(self):
        output = self.tts.retrieve_audio("hello pollytts")
        if output is None:
            raise Exception(
                'PollyTTS server could not be verified. Please check your '
                'internet connection and credentials.')

    def get_tts_class(self):
        return PollyTTS
