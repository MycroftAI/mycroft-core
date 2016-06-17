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
    def format_result(self, pod_id, text):
        return "<queryresult>\
        <pod id='" + pod_id + "' title = '" + pod_id + "'><subpod>\
        <plaintext>" + text + "</plaintext></subpod></pod></queryresult>"

    def create_result(self, pod_id, value):
        result = self.format_result(pod_id, value)
        return wolframalpha.Result(StringIO(result))

    def test_result_pod(self):
        res = self.create_result("Result", "7")
        self.assertEquals(WolframAlphaSkill().get_result(res), "7")

    def test_value_pod(self):
        res = self.create_result("Value", "2^3")
        self.assertEquals(WolframAlphaSkill().get_result(res), "2^3")

    def test_notable_facts_pod(self):
        res = self.create_result("NotableFacts:PeopleData", "PeopleData")
        self.assertEquals(WolframAlphaSkill().get_result(res), "PeopleData")

    def test_basic_information_pod(self):
        res = self.create_result("BasicInformation:PeopleData",
                                 "Born in 1997")
        self.assertEquals(WolframAlphaSkill().get_result(res), "Born in 1997")

    def test_decimal_approximation_pod(self):
        res = self.create_result("DecimalApproximation", "5.6666666666")
        self.assertEquals(WolframAlphaSkill().get_result(res), "5.666")

    def test_invalid_pod(self):
        res = self.create_result("InvalidTitle", "Test")
        self.assertEquals(WolframAlphaSkill().get_result(res), None)

    def test_whitespace_process(self):
        self.assertEquals(WolframAlphaSkill().process_wolfram_string
                          ("Test     string"), "Test string")

    def test_pipe_process(self):
        self.assertEquals(WolframAlphaSkill().process_wolfram_string
                          ("Test | string"), "Test, string")

    def test_newline_process(self):
        self.assertEquals(WolframAlphaSkill().process_wolfram_string
                          ("Test\nstring"), "Test, string")

    def test_factorial_process(self):
        self.assertEquals(WolframAlphaSkill().process_wolfram_string
                          ("Test!"), "Test,factorial")
