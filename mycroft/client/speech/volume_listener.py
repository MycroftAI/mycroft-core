""" Functions for reading the volume level. """

import pyaudio
import struct
import math
from mycroft.util import find_input_device

FORMAT = pyaudio.paInt16
SHORT_NORMALIZE = (1.0/32768.0)
CHANNELS = 2
RATE = 44100
INPUT_BLOCK_TIME = 0.05
INPUT_FRAMES_PER_BLOCK = int(RATE*INPUT_BLOCK_TIME)


def get_rms(block):
    """ RMS amplitude is defined as the square root of the
    mean over time of the square of the amplitude.
     so we need to convert this string of bytes into
     a string of 16-bit samples...
    """
    # we will get one short out for each
    # two chars in the string.
    count = len(block) / 2
    format = "%dh" % (count)
    shorts = struct.unpack(format, block)

    # iterate over the block.
    sum_squares = 0.0
    for sample in shorts:
        # sample is a signed short in +/- 32768.
        # normalize it to 1.0
        n = sample * SHORT_NORMALIZE
        sum_squares += n * n

    return math.sqrt(sum_squares / count)


def open_mic_stream(pa, device_index, device_name):
    """ Open microphone stream from first best microphone device. """
    if not device_index and device_name:
        device_index = find_input_device(device_name)

    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, input_device_index=device_index,
                     frames_per_buffer=INPUT_FRAMES_PER_BLOCK)

    return stream


def read_file_from(filename, bytefrom):
    """ Read listener level from offset. """
    with open(filename, 'r') as fh:
        meter_cur = None
        fh.seek(bytefrom)
        while True:
            line = fh.readline()
            if line == "":
                break

            # Just adjust meter settings
            # Ex:Energy:  cur=4 thresh=1.5
            parts = line.split("=")
            meter_thresh = float(parts[-1])
            meter_cur = float(parts[-2].split(" ")[0])
        return meter_cur
