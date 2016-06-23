import os
import wave
from glob import glob

import pyee
from os.path import dirname, join
from speech_recognition import AudioSource
from mycroft.client.speech.local_recognizer import LocalRecognizer
from mycroft.client.speech.mic import ResponsiveRecognizer
from mycroft.util.log import getLogger
from mycroft.client.speech.mic import logger as speech_logger

__author__ = 'wolfgange3311999'
logger = getLogger('audio_test_runner')


class FileStream(object):
    def __init__(self, file_name):
        self.file = wave.open(file_name, 'rb')
        self.size = self.file.getnframes()
        self.sample_rate = self.file.getframerate()
        self.sample_width = self.file.getsampwidth()

    def read(self, chunk_size):
        if abs(self.file.tell() - self.size) < 10:
            raise EOFError
        return self.file.readframes(chunk_size)

    def close(self):
        self.file.close()


class FileMockMicrophone(AudioSource):
    def __init__(self, file_name):
        self.stream = FileStream(file_name)
        self.SAMPLE_RATE = self.stream.sample_rate
        self.SAMPLE_WIDTH = self.stream.sample_width
        self.CHUNK = 1024

    def close(self):
        self.stream.close()


class AudioTester(object):
    def __init__(self, samp_rate):
        self.ww_recognizer = LocalRecognizer(samp_rate, 'en-us')
        self.listener = ResponsiveRecognizer(self.ww_recognizer)
        speech_logger.setLevel(100)  # Disables logging to clean output

    def test_audio(self, file_name):
        source = FileMockMicrophone(file_name)
        ee = pyee.EventEmitter()

        class SharedData:
            found = False

        def on_found_wake_word():
            SharedData.found = True

        ee.on('recognizer_loop:record_begin', on_found_wake_word)

        try:
            self.listener.listen(source, ee)
        except EOFError:
            pass

        return SharedData.found


BOLD = '\033[1m'
NORMAL = '\033[0m'
GREEN = '\033[92m'
RED = '\033[91m'


def bold_str(val):
    return BOLD + str(val) + NORMAL


def get_root_dir():
    return dirname(dirname(__file__))

if __name__ == "__main__":
    directory = join('audio-accuracy-test', 'data', 'query_after')
    query = join(directory, '*.wav')
    root_dir = get_root_dir()
    full_path = join(root_dir, query)
    file_names = sorted(glob(full_path))

    num_found = 0
    total = len(file_names)

    if total < 1:
        print(bold_str(RED+"Error: No wav files found in " + directory))
        exit(1)

    # Grab audio format info from first file
    ex_file = wave.open(file_names[0], 'rb')

    print
    tester = AudioTester(ex_file.getframerate())
    print

    for file_name in file_names:
        short_name = os.path.basename(file_name)
        was_found = tester.test_audio(file_name)

        if was_found:
            result_str = GREEN + "Detected "
            num_found += 1
        else:
            result_str = RED + "Not found"

        print("Wake word " + bold_str(result_str) + " - " + short_name)


    def to_percent(numerator, denominator):
        return "{0:.2f}".format((100.0 * numerator) / denominator) + "%"


    print
    print("Found " + bold_str(num_found) + " out of " + bold_str(total))
    print(bold_str(to_percent(num_found, total)) + " accuracy.")
    print
