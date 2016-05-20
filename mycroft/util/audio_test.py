from speech_recognition import Recognizer
from mycroft.client.speech.mic import MutableMicrophone
from mycroft.util import play_wav
import argparse

__author__ = 'seanfitz'
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

    record(args.filename, args.duration)
    play_wav(args.filename)


if __name__ == "__main__":
    main()
