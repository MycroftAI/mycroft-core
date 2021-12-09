from unittest import TestCase, mock

from mycroft.util import get_arch


class TestPlatform(TestCase):
    @mock.patch('os.uname')
    def test_get_arch(self, mock_uname):
        mock_uname.return_value = ('Linux', 'Woodstock', '4.15.0-39-generic',
                                   'Awesome test system Mark 7', 'x86_64')
        self.assertEqual(get_arch(), 'x86_64')
