from unittest import TestCase
from mycroft.util import camel_case_split, get_http, remove_last_slash


class TestStringFunctions(TestCase):
    def test_camel_case_split(self):
        """Check that camel case string is split properly."""
        self.assertEqual(camel_case_split('MyCoolSkill'), 'My Cool Skill')
        self.assertEqual(camel_case_split('MyCOOLSkill'), 'My COOL Skill')

    def test_get_http(self):
        """Check that https-url is correctly transformed to a http-url."""
        self.assertEqual(get_http('https://github.com/'), 'http://github.com/')
        self.assertEqual(get_http('http://github.com/'), 'http://github.com/')
        self.assertEqual(get_http('https://github.com/https'),
                         'http://github.com/https')
        self.assertEqual(get_http('http://https.com/'), 'http://https.com/')

    def test_remove_last_slash(self):
        """Check that the last slash in an url is correctly removed."""
        self.assertEqual(remove_last_slash('https://github.com/'),
                         'https://github.com')
        self.assertEqual(remove_last_slash('https://github.com/hello'),
                         'https://github.com/hello')
        self.assertEqual(remove_last_slash('https://github.com/hello/'),
                         'https://github.com/hello')
