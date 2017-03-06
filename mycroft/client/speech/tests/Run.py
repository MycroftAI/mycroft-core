import mycroft.client.speech.listener
import mycroft.client.speech.mic

import speech_recognition

filename_valid = '/home/amcgee7/Documents/projects/mycroft/mycroft-core/mycroft/client/speech/tests/valid_wake/mycroft_wake_success2017-03-03 11:09:48.368663.wav'

filename_invalid = '/home/amcgee7/Documents/projects/mycroft/mycroft-core/mycroft/client/speech/tests/invalid_wake/testing.wav'

def Run():
    print "Running tests"
    result = TestFile(filename_invalid)
    print "testing ", filename_invalid, " Results ", result
    result = TestFile(filename_valid)
    print "testing ", filename_valid, " Results ", result


def TestFile(src):
    rec = speech_recognition.Recognizer()
    with speech_recognition.AudioFile(src) as audio_file:
        audio = rec.record(audio_file)
    
    try:
        print "Sphinx ",rec.recognize_sphinx(audio)
    except speech_recognition.UnknownValueError:
        print "cound not understand"
    except speech_recognition.RequestError:
        print "Sphinx error"
    
    try:
        print "Google ",rec.recognize_google(audio)
    except speech_recognition.UnknownValueError:
        print "Google didn't understand"
    except speech_recognition.RequestError:
        print "Google Error"
    
    return True;

Run()
