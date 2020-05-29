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
from mycroft.tts.tts import TTS, TTSValidator
from mycroft.configuration import Configuration


class PollyTTS(TTS):
    def __init__(self, lang="en-us", config=None):
        import boto3
        config = config or Configuration.get().get("tts", {}).get("polly", {})
        super(PollyTTS, self).__init__(lang, config, PollyTTSValidator(self),
                                       audio_ext="mp3",
                                       ssml_tags=["speak", "say-as", "voice",
                                                  "prosody", "break",
                                                  "emphasis", "sub", "lang",
                                                  "phoneme", "w", "whisper",
                                                  "amazon:auto-breaths",
                                                  "p", "s", "amazon:effect",
                                                  "mark"])

        self.voice = self.config.get("voice", "Matthew")
        self.key_id = self.config.get("access_key_id", '')
        self.key = self.config.get("secret_access_key", '')
        self.region = self.config.get("region", 'us-east-1')
        self.polly = boto3.Session(aws_access_key_id=self.key_id,
                                   aws_secret_access_key=self.key,
                                   region_name=self.region).client('polly')

    def get_tts(self, sentence, wav_file):
        text_type = "text"
        if self.remove_ssml(sentence) != sentence:
            text_type = "ssml"
            sentence = sentence \
                .replace("\\whispered", "/amazon:effect") \
                .replace("whispered", "amazon:effect name=\"whispered\"")
        response = self.polly.synthesize_speech(
            OutputFormat=self.audio_ext,
            Text=sentence,
            TextType=text_type,
            VoiceId=self.voice)

        with open(wav_file, 'wb') as f:
            f.write(response['AudioStream'].read())
        return (wav_file, None)  # No phonemes

    def describe_voices(self, language_code="en-US"):
        if language_code.islower():
            a, b = language_code.split("-")
            b = b.upper()
            language_code = "-".join([a, b])
        # example 'it-IT' useful to retrieve voices
        voices = self.polly.describe_voices(LanguageCode=language_code)

        return voices


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
        try:
            if not self.tts.voice:
                raise Exception("Polly TTS Voice not configured")
            output = self.tts.describe_voices()
        except TypeError:
            raise Exception(
                'PollyTTS server could not be verified. Please check your '
                'internet connection and credentials.')

    def get_tts_class(self):
        return PollyTTS
