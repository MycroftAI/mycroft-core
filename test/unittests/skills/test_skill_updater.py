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
"""Unit tests for the SkillUpdater class."""
import os
from time import sleep
from xdg import BaseDirectory
from unittest.mock import Mock, patch, PropertyMock

from mycroft.skills.skill_updater import SkillUpdater
from test.unittests.base import MycroftUnitTestBase


class TestSkillUpdater(MycroftUnitTestBase):
    mock_package = 'mycroft.skills.skill_updater.'
    use_msm_mock = True

    def setUp(self):
        super().setUp()
        self._mock_time()
        self._mock_connected()

    def _mock_connected(self):
        """Define a mock object representing the connected() function."""
        connected_patch = patch(self.mock_package + 'connected')
        self.addCleanup(connected_patch.stop)
        self.connected_mock = connected_patch.start()
        self.connected_mock.return_value = True

    def _mock_time(self):
        """Define a mock object representing the built-in time function.

        For the purposes of unit tests, we don't really care about the actual
        time.  To have the tests produce predictable results, we just need
        the time() function to return a value we can depend on.
        """
        time_patch = patch(self.mock_package + 'time')
        self.addCleanup(time_patch.stop)
        self.time_mock = time_patch.start()
        self.time_mock.return_value = 100

    def test_load_installed_skills(self):
        """Test loading a set of installed skills into an instance attribute"""
        skill_file_path = str(self.temp_dir.joinpath('.mycroft_skills'))
        with open(skill_file_path, 'w') as skill_file:
            skill_file.write('FooSkill\n')
            skill_file.write('BarSkill\n')

        patch_path = (
            self.mock_package +
            'SkillUpdater.installed_skills_file_path'
        )
        with patch(patch_path, new_callable=PropertyMock) as mock_file_path:
            mock_file_path.return_value = skill_file_path
            updater = SkillUpdater(self.message_bus_mock)
            updater._load_installed_skills()

        self.assertEqual({'FooSkill', 'BarSkill'}, updater.installed_skills)

    def test_apply_install_or_update(self):
        """Test invoking MSM to install or update skills"""
        skill = self._build_mock_msm_skill_list()
        self.msm_mock.list_all_defaults.return_value = [skill]
        updater = SkillUpdater(self.message_bus_mock)
        updater._apply_install_or_update(quick=False)

        self.msm_mock.apply.assert_called_once_with(
            updater.install_or_update,
            self.msm_mock.list(),
            max_threads=2
        )

    def test_apply_install_or_update_quick(self):
        """Test invoking MSM to install or update skills quickly"""
        skill = self._build_mock_msm_skill_list()
        self.msm_mock.list_all_defaults.return_value = [skill]
        updater = SkillUpdater(self.message_bus_mock)
        updater._apply_install_or_update(quick=True)

        self.msm_mock.apply.assert_called_once_with(
            updater.install_or_update,
            self.msm_mock.list(),
            max_threads=20
        )

    def test_apply_install_or_update_missing_defaults(self):
        """Test invoking MSM to install missing default skills"""
        skill = self._build_mock_msm_skill_list()
        skill.is_local = False
        self.msm_mock.list_all_defaults.return_value = [skill]
        updater = SkillUpdater(self.message_bus_mock)
        updater._apply_install_or_update(quick=True)

        self.msm_mock.apply.assert_called_once_with(
            updater.install_or_update,
            self.msm_mock.list(),
            max_threads=20
        )

    def test_save_installed_skills(self):
        """Test saving list of installed skills to a file."""
        skill_file_path = str(self.temp_dir.joinpath('.mycroft_skills'))
        patch_path = (
            self.mock_package +
            'SkillUpdater.installed_skills_file_path'
        )
        with patch(patch_path, new_callable=PropertyMock) as mock_file:
            mock_file.return_value = skill_file_path
            updater = SkillUpdater(self.message_bus_mock)
            updater.installed_skills = ['FooSkill', 'BarSkill']
            updater._save_installed_skills()

        with open(skill_file_path) as skill_file:
            skills = skill_file.readlines()

        self.assertListEqual(['FooSkill\n', 'BarSkill\n'], skills)

    def test_installed_skills_path_virtual_env(self):
        """Test the property representing the installed skill file path."""
        with patch(self.mock_package + 'sys', spec=True) as sys_mock:
            sys_mock.executable = 'path/to/the/virtual_env/bin/python'
            with patch(self.mock_package + 'os.access') as os_patch:
                os_patch.return_value = True
                updater = SkillUpdater(self.message_bus_mock)
                self.assertEqual(
                    'path/to/the/virtual_env/.mycroft-skills',
                    updater.installed_skills_file_path
                )

    def test_installed_skills_path_not_virtual_env(self):
        """Test the property representing the installed skill file path."""
        with patch(self.mock_package + 'os.access') as os_patch:
            os_patch.return_value = False
            updater = SkillUpdater(self.message_bus_mock)
            self.assertEqual(
                os.path.join(BaseDirectory.save_data_path('mycroft'),
                             '.mycroft-skills'),
                updater.installed_skills_file_path
            )

    def test_default_skill_names(self):
        """Test the property representing the list of default skills."""
        updater = SkillUpdater(self.message_bus_mock)
        self.assertIn('time', updater.default_skill_names)
        self.assertIn('weather', updater.default_skill_names)
        self.assertIn('test_skill', updater.default_skill_names)

    def test_download_skills_not_connected(self):
        """Test the error that occurs when the device is not connected."""
        with patch(self.mock_package + 'connected') as connected_mock:
            connected_mock.return_value = False
            with patch(self.mock_package + 'time', spec=True) as time_mock:
                time_mock.return_value = 100
                updater = SkillUpdater(self.message_bus_mock)
                result = updater.update_skills()

        self.assertFalse(result)
        self.assertEqual(400, updater.next_download)

    def test_post_manifest_allowed(self):
        """Test calling the skill manifest API endpoint"""
        self.msm_mock.device_skill_state = 'foo'
        with patch(self.mock_package + 'is_paired') as paired_mock:
            paired_mock.return_value = True
            with patch(self.mock_package + 'DeviceApi', spec=True) as api_mock:
                SkillUpdater(self.message_bus_mock).post_manifest()
                api_instance = api_mock.return_value
                api_instance.upload_skills_data.assert_called_once_with('foo')
            paired_mock.assert_called_once_with()

    def test_install_or_update_beta(self):
        """Test calling install_or_update with a beta skill."""
        self.msm_mock.device_skill_state['skills'][0]['beta'] = True
        skill = self._build_mock_msm_skill_list()
        skill.is_local = False
        updater = SkillUpdater(self.message_bus_mock)
        updater.install_or_update(skill)
        self.assertIn('foobar', updater.installed_skills)
        self.assertIsNone(skill.sha)

    def test_install_or_update_local(self):
        """Test calling install_or_update with a local skill"""
        skill = self._build_mock_msm_skill_list()
        updater = SkillUpdater(self.message_bus_mock)
        updater.install_or_update(skill)
        self.assertIn('foobar', updater.installed_skills)
        skill.update.assert_called_once_with()
        skill.update_deps.assert_called_once_with()
        self.msm_mock.install.assert_not_called()

    def test_install_or_update_default(self):
        """Test calling install_or_update with a default skill"""
        skill = self._build_mock_msm_skill_list()
        skill.name = 'test_skill'
        skill.is_local = False
        updater = SkillUpdater(self.message_bus_mock)
        updater.install_or_update(skill)
        self.assertIn('test_skill', updater.installed_skills)
        self.assertTrue(not skill.update.called)
        self.msm_mock.install.assert_called_once_with(skill, origin='default')

    def test_install_or_update_default_fail(self):
        """Test calling install_or_update with a failed install result"""
        skill = self._build_mock_msm_skill_list()
        skill.name = 'test_skill'
        skill.is_local = False
        self.msm_mock.install.side_effect = ValueError
        updater = SkillUpdater(self.message_bus_mock)
        with self.assertRaises(ValueError):
            updater.install_or_update(skill)
        self.assertNotIn('test_skill', updater.installed_skills)
        self.assertTrue(not skill.update.called)
        self.msm_mock.install.assert_called_once_with(skill, origin='default')
        self.assertTrue(updater.default_skill_install_error)

    def _build_mock_msm_skill_list(self):
        """Helper method to build a mock MSM skill instance."""
        skill = Mock()
        skill.name = 'foobar'
        skill.is_local = True
        skill.sha = None
        skill.install = Mock()
        skill.update = Mock()
        skill.update_deps = Mock()
        skill.path = str(self.temp_dir.joinpath('foobar'))

        return skill

    def test_schedule_retry(self):
        """Test scheduling a retry of a failed install."""
        updater = SkillUpdater(self.message_bus_mock)
        updater._schedule_retry()
        self.assertEqual(1, updater.install_retries)
        self.assertEqual(400, updater.next_download)
        self.assertFalse(updater.default_skill_install_error)

    def test_update_download_time(self):
        """Test updating the next time a download will occur."""
        dot_msm_path = self.temp_dir.joinpath('.msm')
        dot_msm_path.touch()
        dot_msm_mtime_before = dot_msm_path.stat().st_mtime
        sleep(0.5)
        SkillUpdater(self.message_bus_mock)._update_download_time()
        dot_msm_mtime_after = dot_msm_path.stat().st_mtime
        self.assertLess(dot_msm_mtime_before, dot_msm_mtime_after)
