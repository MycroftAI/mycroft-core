# Copyright 2019 Mycroft AI Inc.
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

from .tts import TTS, TTSValidator
from mycroft.configuration import Configuration

from google.cloud import texttospeech
from google.oauth2 import service_account

VOICE_LIST = {
    "male": texttospeech.SsmlVoiceGender.MALE,
    "female": texttospeech.SsmlVoiceGender.FEMALE
}

OUTPUT_FILE_FORMAT = {
    "wav": texttospeech.AudioEncoding.LINEAR16,
    "mp3": texttospeech.AudioEncoding.MP3
}


class GoogleCloudTTS(TTS):

    def __init__(self, lang, config):
        self.config = (Configuration.get().get("tts", {})
                       .get("google_cloud", {}))

        self.type = self.config.get("file_format", "wav").lower()
        super(GoogleCloudTTS, self).__init__(lang, config,
                                             GoogleCloudTTSValidator(self),
                                             audio_ext=self.type)
        self.lang = self.config.get("lang", lang)

        voice_gender = self.config.get("voice_gender", "male").lower()

        service_account_info = self.config.get("service_account_info", {})

        credentials = (service_account.Credentials
                       .from_service_account_info(service_account_info))

        # Instantiates a client
        self.client = texttospeech.TextToSpeechClient(credentials=credentials)

        # Select the language code and the ssml voice gender
        self.voice = texttospeech.VoiceSelectionParams(
            language_code=self.lang, ssml_gender=VOICE_LIST.get(voice_gender)
        )

        # Select the type of audio file you want returned
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=OUTPUT_FILE_FORMAT.get(self.type)
        )

    def get_tts(self, sentence, audio_file):
        with open(audio_file, "wb") as out:
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=sentence)

            # Perform the text-to-speech request on the text input
            # with the selected voice parameters and audio file type
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=self.voice,
                audio_config=self.audio_config
            )

            out.write(response.audio_content)
        return audio_file, None  # No phonemes


class GoogleCloudTTSValidator(TTSValidator):
    def __init__(self, tts):
        super(GoogleCloudTTSValidator, self).__init__(tts)

    def validate_lang(self):
        pass

    def validate_connection(self):
        try:
            synthesis_input = texttospeech.SynthesisInput(text="Test")

            self.tts.client.synthesize_speech(
                input=synthesis_input, voice=self.tts.voice,
                audio_config=self.tts.audio_config
            )
        except Exception as ex:
            raise Exception(
                'Error connecting to Google Cloud TTS server. '
                'Please check your internet connection '
                'and configuration settings', ex)

    def get_tts_class(self):
        return GoogleCloudTTS
