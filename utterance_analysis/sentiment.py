from flair.models import TextClassifier
from flair.data import Sentence

def analyze(utterance: str):
    classifier = TextClassifier.load('en-sentiment')
    sentence = Sentence(utterance)
    classifier.predict(sentence)
    print('Sentence above is: ', sentence.labels)
    return sentence.labels