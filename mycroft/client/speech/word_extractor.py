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
from speech_recognition import AudioData


class WordExtractor:
    SILENCE_SECS = 0.1
    PRECISION_RATE = 0.01

    def __init__(self, audio, recognizer, metrics):
        self.audio = audio
        self.recognizer = recognizer
        self.audio_size = len(self.audio.frame_data)
        self.delta = int(self.audio_size / 2)
        self.begin = 0
        self.end = self.audio_size
        self.precision = int(self.audio_size * self.PRECISION_RATE)
        self.silence_data = self.create_silence(self.SILENCE_SECS,
                                                self.audio.sample_rate,
                                                self.audio.sample_width)
        self.metrics = metrics

    def __add(self, is_begin, value):
        if is_begin:
            self.begin += value
        else:
            self.end += value

    def __calculate_marker(self, is_begin):
        dt = self.delta
        sign = 1 if is_begin else -1

        while dt > self.precision:
            self.__add(is_begin, dt * sign)
            segment = self.audio.frame_data[self.begin:self.end]
            found = self.recognizer.is_recognized(segment, self.metrics)
            if not found:
                self.__add(is_begin, dt * -sign)
            dt = int(dt / 2)

    def calculate_range(self):
        self.__calculate_marker(False)
        self.__calculate_marker(True)

    @staticmethod
    def create_silence(seconds, sample_rate, sample_width):
        return '\0' * int(seconds * sample_rate * sample_width)

    def get_audio_data_before(self):
        byte_data = self.audio.frame_data[0:self.begin] + self.silence_data
        return AudioData(byte_data, self.audio.sample_rate,
                         self.audio.sample_width)

    def get_audio_data_after(self):
        byte_data = self.silence_data + self.audio.frame_data[self.end:
                                                              self.audio_size]
        return AudioData(byte_data, self.audio.sample_rate,
                         self.audio.sample_width)
