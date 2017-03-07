import os
import mycroft.client.speech.listener
import mycroft.client.speech.local_recognizer
import mycroft.client.speech.mic
from mycroft.configuration import ConfigurationManager

import speech_recognition

valid_dir = '/home/amcgee7/Documents/projects/mycroft/mycroft-core/mycroft/client/speech/tests/valid_wake/'

invalid_dir = '/home/amcgee7/Documents/projects/mycroft/mycroft-core/mycroft/client/speech/tests/invalid_wake/'
filename_valid =  valid_dir + 'mycroft_wake_success2017-03-03 11:09:48.368663.wav'

filename_invalid = invalid_dir + 'testing.wav'

def Setup():
    config = ConfigurationManager.get()
    listener_config = config.get('listener')
    wake_word = listener_config.get('wake_word')
    phonemes = listener_config.get('phonemes')
    threshold = listener_config.get('threshold')
    rate = listener_config.get('sample_rate')
    lang = listener_config.get('lang')
    lang = 'en-us'
    print "LocalRecognizer",wake_word, phonemes, threshold, rate, lang
    return mycroft.client.speech.local_recognizer.LocalRecognizer(wake_word, phonemes, threshold, rate, lang)

mycroft_recognizer = Setup()
remote_recognizer = mycroft.client.speech.mic.ResponsiveRecognizer(mycroft_recognizer)


def Run():
    print "Running tests"
    TestValid()
    TestInvalid()

def TestFile(src):
    result = {"sphinx":False,"google":False, "Found Wake Word":False}
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
    
    return result;

def TestValid():
    valid=0
    invalid=0
    files = os.listdir(valid_dir)
    for filex in files:
        filename = valid_dir + filex
        result = TestFile(filename)
        if result["Found Wake Word"]:
            valid = valid + 1;
        else:
            invalid = invalid+ 1;
            print "Valid Fail", filename,result
    print "TestValid, Valid %d InValid %d" % (valid,invalid)

def TestInvalid():
    valid=0
    invalid=0
    files = os.listdir(invalid_dir)
    for filex in files:
        filename = invalid_dir + filex
        result = TestFile(filename)
        if result["Found Wake Word"]:
            valid = valid + 1;
            print "InValid Fail",filename,result
        else:
            invalid = invalid + 1 ;
    print "TestInvalid, InValid %d Valid %d" % (invalid,valid)

Run()
