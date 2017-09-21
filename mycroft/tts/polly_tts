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

import hashlib
import os
import os.path
from contextlib import closing
from tempfile import gettempdir

from mycroft.tts import TTS, TTSValidator
from mycroft.configuration import ConfigurationManager
from mycroft.util.log import getLogger
from mycroft.util import play_mp3

logger = getLogger("Polly")

__author__ = 'jarbas'


class Polly(TTS):
    def __init__(self, lang, voice):
        super(Polly, self).__init__(lang, voice, PollyValidator(self))
        config = ConfigurationManager.get().get('tts', {}).get("polly", {})
        try:
            from boto3 import Session
        except:
            logger.error("Missing boto3 python requirement for PollyTTS")
        # FS cache
        self.cache = config.get("cache", True)
        # Voice ID
        self.voice = config.get("voice", 'Joanna')
        # AWS data: if profile is defined it has priority
        self.profile = config.get("profile", 'default')
        self.key_id = config.get("key_id", '')
        self.key = config.get("key", '')
        self.region = config.get("region", 'us-west-2')
        if self.profile:
            # create a client using the credentials and region defined
            # in the AWS_PROFILE section of the AWS credentials and config files
            session = Session(profile_name=self.profile)
            logger.info('Using profile name: {0}'.format(self.profile))
        else:
            session = Session(aws_access_key_id=self.key_id,
                              aws_secret_access_key=self.key,
                              region_name=self.region)
            logger.info('Using without credentials and config files')

        self.polly = session.client('polly')

    def execute(self, sentence, output="/tmp/pico_tts.raw"):
        self.begin_audio()
        output = self.retrieve_audio(sentence)
        if output is None:
            logger.error("Could not get audio from Polly")
        else:
            play_mp3(output)
        self.end_audio()

    def describe_voices(self, language_code):
        # example 'it-IT' useful to retrieve voices
        response = self.polly.describe_voices(LanguageCode=language_code)
        logger.info(response)

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
            logger.info('Using file {0}'.format(output))
            return output

        # call AWS
        try:
            response = self.polly.synthesize_speech(Text=sentence,
                                                    OutputFormat=output_format,
                                                    VoiceId=self.voice)
        except Exception as err:
            logger.error(err)
            return None

        # access the audio stream from the response
        if 'AudioStream' in response:
            with closing(response['AudioStream']) as stream:
                try:
                    # open a file for writing the output as a binary stream
                    with open(output, 'wb') as file:
                        file.write(stream.read())
                        logger.info('Generated new file {0}'.format(output))
                        return output
                except IOError as error:
                    logger.error(error)
                    return None
        logger.error('No AudioStream in response')
        return None


class PollyValidator(TTSValidator):
    def __init__(self, tts):
        super(PollyValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        pass

    def get_tts_class(self):
        return Polly
