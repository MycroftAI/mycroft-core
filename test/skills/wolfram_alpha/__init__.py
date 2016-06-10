import unittest
import wolframalpha
from StringIO import StringIO

from mycroft.skills.wolfram_alpha import WolframAlphaSkill
from mycroft.util.log import getLogger

__author__ = 'eward'

logger = getLogger(__name__)

# necessary amount of text for testing: "<queryresult>\
# <pod id='NotableFacts:PeopleData'><subpod>\
# <plaintext>Test</plaintext></subpod></pod></queryresult>"


class WolframAlphaTest(unittest.TestCase):
    def format_result(self, pod_title, text):
        return "<queryresult>\
        <pod title='" + pod_title + "'><subpod>\
        <plaintext>" + text + "</plaintext></subpod></pod></queryresult>"

    def test_result_pod(self):
        result = self.format_result("Result", "7")
        res = wolframalpha.Result(StringIO(result))
        self.assertEquals(WolframAlphaSkill().get_result(res), "7")

    def test_value_pod(self):
        result = self.format_result("Value", "2^3")
        res = wolframalpha.Result(StringIO(result))
        self.assertEquals(WolframAlphaSkill().get_result(res), "2^3")

    def test_notable_facts_pod(self):
        result = self.format_result("NotableFacts:PeopleData", "PeopleData")
        res = wolframalpha.Result(StringIO(result))
        self.assertEquals(WolframAlphaSkill().get_result(res), "PeopleData")

    def test_basic_information_pod(self):
        result = self.format_result("BasicInformation:PeopleData",
                                    "Born in 1997")
        res = wolframalpha.Result(StringIO(result))
        self.assertEquals(WolframAlphaSkill().get_result(res), "Born in 1997")

    def test_decimal_approximation_pod(self):
        result = self.format_result("DecimalApproximation", "5.6666666666")
        res = wolframalpha.Result(StringIO(result))
        self.assertEquals(WolframAlphaSkill().get_result(res), "5.666")

    def test_invalid_pod(self):
        result = self.format_result("InvalidTitle", "Test")
        res = wolframalpha.Result(StringIO(result))
        self.assertEquals(WolframAlphaSkill().get_result(res), None)
