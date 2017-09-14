import unittest
import mock

import mycroft.version


VERSION_INFO = """
{
    "coreVersion": "1505203453",
    "enclosureVersion": "1.0.0"
}"""


class TestVersion(unittest.TestCase):
    @mock.patch('mycroft.version.CORE_VERSION_MAJOR', 0)
    @mock.patch('mycroft.version.CORE_VERSION_MINOR', 8)
    @mock.patch('mycroft.version.CORE_VERSION_BUILD', 20)
    def test_get_version(self):
        """
            Tests for mycroft.version.get_version()

            Assures that only lower versions return True
        """
        self.assertTrue(mycroft.version.check_version('0.0.1'))
        self.assertTrue(mycroft.version.check_version('0.8.1'))
        self.assertTrue(mycroft.version.check_version('0.8.20'))
        self.assertFalse(mycroft.version.check_version('0.8.22'))
        self.assertFalse(mycroft.version.check_version('0.9.12'))
        self.assertFalse(mycroft.version.check_version('1.0.2'))

    @mock.patch('mycroft.version.isfile')
    @mock.patch('mycroft.version.exists')
    @mock.patch('mycroft.version.open',
                mock.mock_open(read_data=VERSION_INFO), create=True)
    def test_version_manager(self, mock_exists, mock_isfile):
        """
            Test mycroft.version.VersionManager.get()

            asserts that the method returns expected data
        """
        mock_isfile.return_value = True
        mock_exists.return_value = True

        version = mycroft.version.VersionManager.get()
        self.assertEquals(version['coreVersion'], "1505203453")
        self.assertEquals(version['enclosureVersion'], "1.0.0")

        # Check file not existing case
        mock_exists.return_value = False
        version = mycroft.version.VersionManager.get()
        self.assertEquals(version['coreVersion'], None)
        self.assertEquals(version['enclosureVersion'], None)
