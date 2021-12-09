from unittest import TestCase
from mycroft.util import camel_case_split


class TestStringFunctions(TestCase):
    def test_camel_case_split(self):
        """Check that camel case string is split properly."""
        self.assertEqual(camel_case_split('MyCoolSkill'), 'My Cool Skill')
        self.assertEqual(camel_case_split('MyCOOLSkill'), 'My COOL Skill')
