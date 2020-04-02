# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import unittest
from unittest.mock import mock_open, patch

from mycroft.version import check_version, CORE_VERSION_STR, VersionManager


VERSION_INFO = """
{
    "coreVersion": "1505203453",
    "enclosureVersion": "1.0.0"
}"""


class TestVersion(unittest.TestCase):
    @patch('mycroft.version.CORE_VERSION_TUPLE', (0, 8, 20))
    def test_get_version(self):
        """
            Tests for mycroft.version.get_version()

            Assures that only lower versions return True
        """
        self.assertTrue(check_version('0.0.1'))
        self.assertTrue(check_version('0.8.1'))
        self.assertTrue(check_version('0.8.20'))
        self.assertFalse(check_version('0.8.22'))
        self.assertFalse(check_version('0.9.12'))
        self.assertFalse(check_version('1.0.2'))

    @patch('mycroft.version.isfile')
    @patch('mycroft.version.exists')
    @patch('mycroft.version.open',
           mock_open(read_data=VERSION_INFO), create=True)
    def test_version_manager_get(self, mock_exists, mock_isfile):
        """Test mycroft.version.VersionManager.get()

        Asserts that the method returns data from version file
        """
        mock_isfile.return_value = True
        mock_exists.return_value = True

        version = VersionManager.get()
        self.assertEqual(version['coreVersion'], "1505203453")
        self.assertEqual(version['enclosureVersion'], "1.0.0")

    @patch('mycroft.version.exists')
    def test_version_manager_get_no_file(self, mock_exists):
        """Test mycroft.version.VersionManager.get()

        Asserts that the method returns current version if no file exists.
        """
        mock_exists.return_value = False
        version = VersionManager.get()
        self.assertEqual(version['coreVersion'], CORE_VERSION_STR)
        self.assertEqual(version['enclosureVersion'], None)
