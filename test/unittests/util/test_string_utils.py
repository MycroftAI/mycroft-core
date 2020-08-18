from unittest import TestCase
from mycroft.util import camel_case_split, remove_last_slash


class TestStringFunctions(TestCase):
    def test_camel_case_split(self):
        """Check that camel case string is split properly."""
        self.assertEqual(camel_case_split('MyCoolSkill'), 'My Cool Skill')
        self.assertEqual(camel_case_split('MyCOOLSkill'), 'My COOL Skill')

    def test_remove_last_slash(self):
        """Check that the last slash in an url is correctly removed."""
        self.assertEqual(remove_last_slash('https://github.com/'),
                         'https://github.com')
        self.assertEqual(remove_last_slash('https://github.com/hello'),
                         'https://github.com/hello')
        self.assertEqual(remove_last_slash('https://github.com/hello/'),
                         'https://github.com/hello')
