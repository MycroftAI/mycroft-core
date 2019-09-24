# Copyright 2019 Mycroft AI Inc.
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
"""Unit tests for the SkillLoader class."""
from time import time
from unittest.mock import call, MagicMock, Mock, patch

from mycroft.skills.skill_loader import _get_last_modified_time, SkillLoader
from ..base import MycroftUnitTestBase

ONE_MINUTE = 60


class TestSkillLoader(MycroftUnitTestBase):
    mock_package = 'mycroft.skills.skill_loader.'

    def setUp(self):
        super().setUp()
        self.skill_directory = self._load_skill_directory()
        self.loader = SkillLoader(
            self.message_bus_mock,
            str(self.skill_directory)
        )
        self._mock_skill_instance()
        # TODO: un-mock these when they are more testable
        self.loader._load_skill_source = Mock(
            return_value=Mock()
        )
        self.loader._check_for_first_run = Mock()

    def _load_skill_directory(self):
        """The skill loader expects certain things in a skill directory."""
        skill_directory = self.temp_dir.joinpath('test_skill')
        skill_directory.mkdir()
        for file_name in ('__init__.py', 'bar.py', '.foobar', 'bar.pyc'):
            skill_directory.joinpath(file_name).touch()

        return skill_directory

    def _mock_skill_instance(self):
        """Mock the skill instance, we are not testing skill functionality."""
        skill_instance = Mock()
        skill_instance.name = 'test_skill'
        skill_instance.reload_skill = True
        skill_instance.default_shutdown = Mock()
        skill_instance.settings = Mock()
        self.skill_instance_mock = skill_instance

    def test_get_last_modified_date(self):
        """Get the last modified time of files in a path"""
        last_modified_date = _get_last_modified_time(str(self.skill_directory))

        file_path = self.skill_directory.joinpath('bar.py')
        expected_result = file_path.stat().st_mtime
        self.assertEqual(last_modified_date, expected_result)

    def test_skill_already_loaded(self):
        """The loader should take to action for an already loaded skill."""
        self.loader.instance = Mock
        self.loader.instance.reload_skill = True
        self.loader.loaded = True
        self.loader.last_loaded = time() + ONE_MINUTE

        self.assertFalse(self.loader.reload_needed())

    def test_skill_reloading_blocked(self):
        """The loader should skip reloads for skill that doesn't allow it."""
        self.loader.instance = Mock()
        self.loader.instance.reload_skill = False
        self.loader.active = True
        self.loader.loaded = True
        self.assertFalse(self.loader.reload_needed())

    def test_skill_reloading_deactivated(self):
        """The loader should skip reloads for skill that aren't active."""
        self.loader.instance = Mock()
        self.loader.instance.reload_skill = True
        self.loader.active = False
        self.loader.loaded = False
        self.assertFalse(self.loader.reload_needed())

    def test_skill_reload(self):
        """Test reloading a skill that was modified."""
        self.loader.instance = Mock()
        self.loader.loaded = True
        self.loader.last_loaded = 0

        with patch(self.mock_package + 'time') as time_mock:
            time_mock.return_value = 100
            with patch(self.mock_package + 'SettingsMetaUploader'):
                self.loader.reload()

        self.assertTrue(self.loader.load_attempted)
        self.assertTrue(self.loader.loaded)
        self.assertEqual(100, self.loader.last_loaded)
        self.assertListEqual(
            ['mycroft.skills.shutdown', 'mycroft.skills.loaded'],
            self.message_bus_mock.message_types
        )
        log_messages = [
            call.info('ATTEMPTING TO RELOAD SKILL: test_skill'),
            call.info('Skill test_skill shut down successfully'),
            call.info('Skill test_skill loaded successfully')
        ]
        self.assertListEqual(log_messages, self.log_mock.method_calls)

    def test_skill_load(self):
        with patch(self.mock_package + 'time') as time_mock:
            time_mock.return_value = 100
            with patch(self.mock_package + 'SettingsMetaUploader'):
                self.loader.load()

        self.assertTrue(self.loader.load_attempted)
        self.assertTrue(self.loader.loaded)
        self.assertEqual(100, self.loader.last_loaded)
        self.assertListEqual(
            ['mycroft.skills.loaded'],
            self.message_bus_mock.message_types
        )
        log_messages = [
            call.info('ATTEMPTING TO LOAD SKILL: test_skill'),
            call.info('Skill test_skill loaded successfully')
        ]
        self.assertListEqual(log_messages, self.log_mock.method_calls)

    def test_skill_load_blacklisted(self):
        """Skill should not be loaded if it is blacklisted"""
        self.loader.config['skills']['blacklisted_skills'] = ['test_skill']
        with patch(self.mock_package + 'SettingsMetaUploader'):
            self.loader.load()

        self.assertTrue(self.loader.load_attempted)
        self.assertFalse(self.loader.loaded)
        self.assertListEqual(
            ['mycroft.skills.loading_failure'],
            self.message_bus_mock.message_types
        )
        log_messages = [
            call.info('ATTEMPTING TO LOAD SKILL: test_skill'),
            call.info(
                'Skill test_skill is blacklisted - it will not be loaded'
            ),
            call.error('Skill test_skill failed to load')
        ]
        self.assertListEqual(log_messages, self.log_mock.method_calls)
