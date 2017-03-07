"""

This File Tests wake word validataion.  It's ment as a manual test but
could be automated.

Usage
-----
This file is ran from the following command at the root of the project
folder

    $ python -m mycroft.client.speech.tests.Run


Notes
-----
    Wav Files must be in the mycroft/client/speech/tests/invalid_wake/
    and mycroft/client/speech/tests/valid_wake/ folders for the test
    To use in testing.

"""
import os
import mycroft.client.speech.listener
import mycroft.client.speech.local_recognizer
import mycroft.client.speech.mic
from mycroft.configuration import ConfigurationManager

import speech_recognition

valid_dir = '/home/amcgee7/Documents/projects/mycroft/mycroft-core/mycroft/client/speech/tests/valid_wake/'

invalid_dir = '/home/amcgee7/Documents/projects/mycroft/mycroft-core/mycroft/client/speech/tests/invalid_wake/'
filename_valid = valid_dir + 'mycroft_wake_success2017-03-03 11:09:48.368663.wav'

filename_invalid = invalid_dir + 'testing.wav'
""".
valid_dir:  Is the location of valid wav files to test for validation
invalid_dir: is the location of invalid wav files to test for validation
filename_valid: is an example valid file for testing
filename_invalid: is an example invalid file for testing
"""


def Setup():
    """ 
    This Fuction is a setup for Testing
    Creates a LocalRecognizer to pass back too mycroft_recognizer
    """
    config = ConfigurationManager.get()
    listener_config = config.get('listener')
    wake_word = listener_config.get('wake_word')
    phonemes = listener_config.get('phonemes')
    threshold = listener_config.get('threshold')
    rate = listener_config.get('sample_rate')
    lang = listener_config.get('lang')
    lang = 'en-us'
    print "LocalRecognizer", wake_word, phonemes, threshold, rate, lang
    return mycroft.client.speech.local_recognizer.LocalRecognizer(
        wake_word, phonemes, threshold, rate, lang)

mycroft_recognizer = Setup()
remote_recognizer = mycroft.client.speech.mic.ResponsiveRecognizer(
    mycroft_recognizer)
"""
mycroft_recognizer and remote_recognizer: is used for testing valid wake words

"""

def Run():
    """
    For Running the Tests as needed.
    """
    print "Running tests"
    TestValid()
    TestInvalid()


def TestFile(src):
    """
    This tests a give file(src) and returns translations and if it was 
    a valid wake word.
    """
    result = {"sphinx": False, "google": False, "Found Wake Word": False}
    rec = speech_recognition.Recognizer()
    with speech_recognition.AudioFile(src) as audio_file:
        audio = rec.record(audio_file)
        audio_raw = audio.get_raw_data()

    try:
        result["sphinx"] = rec.recognize_sphinx(audio)
    except speech_recognition.UnknownValueError:
        print "cound not understand"
    except speech_recognition.RequestError:
        print "Sphinx error"

    try:
        result["google"] = rec.recognize_google(audio)
    except speech_recognition.UnknownValueError:
        print "Google didn't understand"
    except speech_recognition.RequestError:
        print "Google Error"

    try:
        if remote_recognizer.wake_word_in_audio(audio_raw):
            result["Found Wake Word"] = True
    except:
        print "Error Finding Wake Word"

    return result


def TestValid():
    """
    This searches files in the valid folder and tests them for valid
    wake words.  Reports any problems and prints the status of the tests.
    """
    valid = 0
    invalid = 0
    files = os.listdir(valid_dir)
    for filex in files:
        filename = valid_dir + filex
        result = TestFile(filename)
        if result["Found Wake Word"]:
            valid = valid + 1
        else:
            invalid = invalid + 1
            print "Valid Fail", filename, result
    print "TestValid, Valid %d InValid %d" % (valid, invalid)


def TestInvalid():
    """
    This searches files in the invalid folder and tests them for valid
    wake words.  Reports any problems and prints the status of the tests.
    """
    valid = 0
    invalid = 0
    files = os.listdir(invalid_dir)
    for filex in files:
        filename = invalid_dir + filex
        result = TestFile(filename)
        if result["Found Wake Word"]:
            valid = valid + 1
            print "InValid Fail", filename, result
        else:
            invalid = invalid + 1
    print "TestInvalid, InValid %d Valid %d" % (invalid, valid)

Run()
"""Run the test once imported."""
