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
import argparse

from speech_recognition import Recognizer

from mycroft.client.speech.mic import MutableMicrophone
from mycroft.util import play_wav

"""
Audio Test
A tool for recording X seconds of audio, and then playing them back. Useful
for testing hardware, and ensures
compatibility with mycroft recognizer loop code.
"""


def record(filename, duration):
    mic = MutableMicrophone()
    recognizer = Recognizer()
    with mic as source:
        audio = recognizer.record(source, duration=duration)
        with open(filename, 'wb') as f:
            f.write(audio.get_wav_data())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f', '--filename', dest='filename', default="/tmp/test.wav",
        help="Filename for saved audio (Default: /tmp/test.wav)")
    parser.add_argument(
        '-d', '--duration', dest='duration', type=int, default=10,
        help="Duration of recording in seconds (Default: 10)")
    args = parser.parse_args()

    print(" ===========================================================")
    print(" ==         STARTING TO RECORD, MAKE SOME NOISE!          ==")
    print(" ===========================================================")

    record(args.filename, args.duration)

    print(" ===========================================================")
    print(" ==           DONE RECORDING, PLAYING BACK...             ==")
    print(" ===========================================================")
    play_wav(args.filename)


if __name__ == "__main__":
    main()
