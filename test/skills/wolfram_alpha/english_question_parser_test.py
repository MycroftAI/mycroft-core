import unittest

from mycroft.skills.wolfram_alpha import EnglishQuestionParser

__author__ = 'wolfgange3311999'


class EnglishQuestionParserTest(unittest.TestCase):
    parser = EnglishQuestionParser()
    test_jsons = [
        {
            'utterance': 'who is abraham lincoln',
            'parsed_question': {
                'QuestionWord': 'who',
                'QuestionVerb': 'is',
                'Query': 'abraham lincoln'
            }
        },
        {
            'utterance': 'what\'s a dog',
            'parsed_question': {
                'QuestionWord': 'what',
                'QuestionVerb': '\'s',
                'Query': 'a dog'
            }
        },
        {
            'utterance': 'who did this',
            'parsed_question': {
                'QuestionWord': 'who',
                'QuestionVerb': 'did',
                'Query': 'this'
            }
        }
    ]

    def test_question_parsing(self):
        for test_json in self.test_jsons:
            parsed_question = self.parser.parse(test_json['utterance'])
            self.assertEquals(parsed_question, test_json['parsed_question'])
