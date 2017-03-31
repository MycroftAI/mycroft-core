import os
import time
import wave
from glob import glob
from os.path import dirname, join

import pyee
from speech_recognition import AudioSource

from mycroft.client.speech.listener import RecognizerLoop
from mycroft.client.speech.mic import ResponsiveRecognizer
from mycroft.client.speech.mic import logger as speech_logger
from mycroft.util.log import getLogger

__author__ = 'wolfgange3311999'
logger = getLogger('audio_test_runner')


def to_percent(val):
    return "{0:.2f}".format(100.0 * val) + "%"


class FileStream(object):
    MIN_S_TO_DEBUG = 5.0

    # How long between printing debug info to screen
    UPDATE_INTERVAL_S = 1.0

    def __init__(self, file_name):
        self.file = wave.open(file_name, 'rb')
        self.size = self.file.getnframes()
        self.sample_rate = self.file.getframerate()
        self.sample_width = self.file.getsampwidth()
        self.last_update_time = 0.0

        self.total_s = self.size / self.sample_rate / self.sample_width
        if self.total_s > self.MIN_S_TO_DEBUG:
            self.debug = True
        else:
            self.debug = False

    def calc_progress(self):
        return float(self.file.tell()) / self.size

    def read(self, chunk_size):

        progress = self.calc_progress()
        if progress == 1.0:
            raise EOFError

        if self.debug:
            cur_time = time.time()
            dt = cur_time - self.last_update_time
            if dt > self.UPDATE_INTERVAL_S:
                self.last_update_time = cur_time
                print(to_percent(progress))

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
        print  # Pad debug messages
        self.ww_recognizer = RecognizerLoop.create_mycroft_recognizer(
            samp_rate, 'en-us')
        self.listener = ResponsiveRecognizer(self.ww_recognizer)
        print
        speech_logger.setLevel(100)  # Disables logging to clean output

    def test_audio(self, file_name):
        source = FileMockMicrophone(file_name)
        ee = pyee.EventEmitter()

        class SharedData:
            times_found = 0

        def on_found_wake_word():
            SharedData.times_found += 1

        ee.on('recognizer_loop:record_begin', on_found_wake_word)

        try:
            while True:
                self.listener.listen(source, ee)
        except EOFError:
            pass

        return SharedData.times_found


class Color:
    BOLD = '\033[1m'
    NORMAL = '\033[0m'
    GREEN = '\033[92m'
    RED = '\033[91m'


def bold_str(val):
    return Color.BOLD + str(val) + Color.NORMAL


def get_root_dir():
    return dirname(dirname(__file__))


def get_file_names(folder):
    query = join(folder, '*.wav')
    root_dir = get_root_dir()
    full_path = join(root_dir, query)
    file_names = sorted(glob(full_path))

    if len(file_names) < 1:
        raise IOError

    return file_names


def test_audio_files(tester, file_names, on_file_finish):
    num_found = 0
    for file_name in file_names:
        short_name = os.path.basename(file_name)
        times_found = tester.test_audio(file_name)

        num_found += times_found
        on_file_finish(short_name, times_found)

    return num_found


def file_frame_rate(file_name):
    wf = wave.open(file_name, 'rb')
    frame_rate = wf.getframerate()
    wf.close()
    return frame_rate


def print_ww_found_status(word, short_name):
    print("Wake word " + bold_str(word) + " - " + short_name)


def test_false_negative(directory):
    file_names = get_file_names(directory)

    # Grab audio format info from first file
    tester = AudioTester(file_frame_rate(file_names[0]))

    def on_file_finish(short_name, times_found):
        not_found_str = Color.RED + "Not found"
        found_str = Color.GREEN + "Detected "
        status_str = not_found_str if times_found == 0 else found_str
        print_ww_found_status(status_str, short_name)

    num_found = test_audio_files(tester, file_names, on_file_finish)
    total = len(file_names)

    print
    print("Found " + bold_str(num_found) + " out of " + bold_str(total))
    print(bold_str(to_percent(float(num_found) / total)) + " accuracy.")
    print


def test_false_positive(directory):
    file_names = get_file_names(directory)

    # Grab audio format info from first file
    tester = AudioTester(file_frame_rate(file_names[0]))

    def on_file_finish(short_name, times_found):
        not_found_str = Color.GREEN + "Not found"
        found_str = Color.RED + "Detected "
        status_str = not_found_str if times_found == 0 else found_str
        print_ww_found_status(status_str, short_name)

    num_found = test_audio_files(tester, file_names, on_file_finish)
    total = len(file_names)

    print
    print("Found " + bold_str(num_found) + " false positives")
    print("in " + bold_str(str(total)) + " files")
    print


def run_test():
    directory = join('audio-accuracy-test', 'data')

    false_neg_dir = join(directory, 'with_wake_word', 'query_after')
    false_pos_dir = join(directory, 'without_wake_word')

    try:
        test_false_negative(false_neg_dir)
    except IOError:
        print(bold_str("Warning: No wav files found in " + false_neg_dir))

    try:
        test_false_positive(false_pos_dir)
    except IOError:
        print(bold_str("Warning: No wav files found in " + false_pos_dir))

    print("Complete!")


if __name__ == "__main__":
    run_test()
