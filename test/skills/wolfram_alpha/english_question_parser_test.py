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
            'utterance': 'what are they',
            'parsed_question': {
                'QuestionWord': 'what',
                'QuestionVerb': 'are',
                'Query': 'they'
            }
        },
        {
            'utterance': 'when was this',
            'parsed_question': {
                'QuestionWord': 'when',
                'QuestionVerb': 'was',
                'Query': 'this'
            }
        },
        {
            'utterance': 'why were they there',
            'parsed_question': {
                'QuestionWord': 'why',
                'QuestionVerb': 'were',
                'Query': 'they there'
            }
        },
        {
            'utterance': 'which is the thing',
            'parsed_question': {
                'QuestionWord': 'which',
                'QuestionVerb': 'is',
                'Query': 'the thing'
            }
        },
        {
            'utterance': 'who saw abraham lincoln',
            'parsed_question': {
                'QuestionWord': 'who',
                'QuestionVerb': 'saw',
                'Query': 'abraham lincoln'
            }
        },
        {
            'utterance': 'what began life',
            'parsed_question': {
                'QuestionWord': 'what',
                'QuestionVerb': 'began',
                'Query': 'life'
            }
        },
        {
            'utterance': 'where sat the person',
            'parsed_question': {
                'QuestionWord': 'where',
                'QuestionVerb': 'sat',
                'Query': 'the person'
            }
        },
        {
            'utterance': 'i like stuff',
            'parsed_question': None
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
