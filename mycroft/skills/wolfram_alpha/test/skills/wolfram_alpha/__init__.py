import unittest
import wolframalpha
from StringIO import StringIO

from mycroft.skills.wolfram_alpha import WolframAlphaSkill

__author__ = 'eward'

# necessary amount of text for testing: "<queryresult>\
# <pod id='NotableFacts:PeopleData'><subpod>\
# <plaintext>Test</plaintext></subpod></pod></queryresult>"


class WolframAlphaTest(unittest.TestCase):
    def test_get_results(self):
        result = "<queryresult>\
        <pod id='NotableFacts:PeopleData'><subpod>\
        <plaintext>Test</plaintext></subpod></pod></queryresult>"
        res = wolframalpha.Result(StringIO(result))
        self.assertEquals(WolframAlphaSkill.get_result(res), "Test")
