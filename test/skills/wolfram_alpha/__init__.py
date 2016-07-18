import unittest
import wolframalpha
from StringIO import StringIO

from mycroft.skills.wolfram_alpha import WolframAlphaSkill
from mycroft.util.log import getLogger

__author__ = 'eward'

logger = getLogger(__name__)


class WolframAlphaTest(unittest.TestCase):
    skill = WolframAlphaSkill()

    @staticmethod
    def format_result(pod_id, text, pod_num):
        return "<queryresult>\
        <pod id='" + pod_id + "' title = '" + pod_id + \
               "' position='" + pod_num + "'><subpod> \
        <plaintext>" + text + "</plaintext></subpod></pod></queryresult>"

    @staticmethod
    def format_did_you_mean(text):
        tree = "<queryresult><didyoumeans>"
        for result in text:
            tree += "<didyoumean>" + result + "</didyoumean>"
        tree += "</didyoumeans></queryresult>"
        return tree

    def create_result(self, pod_id, value, pod_num):
        result = self.format_result(pod_id, value, pod_num)
        return wolframalpha.Result(StringIO(result))

    def create_did_you_mean(self, text):
        test = self.format_did_you_mean(text)
        return wolframalpha.Result(StringIO(test))

    def test_result_pod(self):
        res = self.create_result("Result", "7", '300')
        self.assertEquals(self.skill.get_result(res), "7")

    def test_value_pod(self):
        res = self.create_result("Value", "2^3", '300')
        self.assertEquals(self.skill.get_result(res), "2^3")

    def test_notable_facts_pod(self):
        res = self.create_result("NotableFacts:PeopleData",
                                 "PeopleData", '300')
        self.assertEquals(self.skill.get_result(res), "PeopleData")

    def test_basic_information_pod(self):
        res = self.create_result("BasicInformation:PeopleData",
                                 "Born in 1997", '300')
        self.assertEquals(self.skill.get_result(res), "Born in 1997")

    def test_decimal_approximation_pod(self):
        res = self.create_result("DecimalApproximation", "5.6666666666", '300')
        self.assertEquals(self.skill.get_result(res), "5.666")

    def test_definition_pod(self):
        res = self.create_result("Definition:WordData",
                                 "a cat is a feline", '300')
        self.assertEquals(self.skill.get_result(res),
                          "a cat is a feline")

    def test_numbered_pod(self):
        res = self.create_result("MathConcept", "tangrams are objects", '200')
        self.assertEqual(self.skill.get_result(res),
                         "tangrams are objects")

    def test_invalid_pod(self):
        res = self.create_result("InvalidTitle", "Test", '300')
        self.assertEquals(self.skill.get_result(res), None)

    def test_whitespace_process(self):
        self.assertEquals(self.skill.process_wolfram_string
                          ("Test     string"), "Test string")

    def test_pipe_process(self):
        self.assertEquals(self.skill.process_wolfram_string
                          ("Test | string"), "Test, string")

    def test_newline_process(self):
        self.assertEquals(self.skill.process_wolfram_string
                          ("Test\nstring"), "Test, string")

    def test_factorial_process(self):
        self.assertEquals(self.skill.process_wolfram_string
                          ("Test!"), "Test,factorial")

    def test_find_did_you_mean_exists(self):
        values = ['search for power', 'power']
        res = self.create_did_you_mean(values)
        self.assertEquals(self.skill._find_did_you_mean(res),
                          values)

    def test_find_did_you_mean_none(self):
        res = self.create_did_you_mean([])
        self.assertEquals(self.skill._find_did_you_mean(res), [])
