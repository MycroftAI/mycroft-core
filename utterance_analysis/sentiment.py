from time import time
from flair.models import TextClassifier
from flair.data import Sentence

def analyze(utterance: str, classifier):
    sentence = Sentence(utterance)
    classifier.predict(sentence)
    return sentence.labels