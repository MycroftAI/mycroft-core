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
import tempfile
from os import path
from shutil import rmtree
from time import sleep, time
from unittest import TestCase
from unittest.mock import Mock, patch, PropertyMock

from msm import MycroftSkillsManager
from msm.skill_repo import SkillRepo
from msm.util import MsmProcessLock
from pathlib import Path

from mycroft.skills.skill_updater import SkillUpdater

MOCK_PACKAGE = 'mycroft.skills.skill_update.'


class MockMessageBus:
    def __init__(self):
        self.message_types = []
        self.message_data = []
        self.event_handlers = []

    def emit(self, message):
        self.message_types.append(message.type)
        self.message_data.append(message.data)

    def on(self, event, _):
        self.event_handlers.append(event)


class TestSkillUpdater(TestCase):
    def setUp(self):
        self.message_bus = MockMessageBus()
        self.temp_dir = tempfile.mkdtemp()
        self._mock_msm()
        self._mock_config()
        self._mock_time()
        self._mock_connected()
        self._mock_dialog()

    def _mock_msm(self):
        """Define a mock object representing the MycroftSkillsManager."""
        msm_patch = patch(MOCK_PACKAGE + 'create_msm')
        self.addCleanup(msm_patch.stop)
        self.create_msm_mock = msm_patch.start()
        self.msm_mock = Mock(spec=MycroftSkillsManager)
        self.msm_mock.skills_dir = self.temp_dir
        self.msm_mock.platform = 'test_platform'
        self.msm_mock.lock = MsmProcessLock()
        self.msm_mock.repo = Mock(spec=SkillRepo)
        self.msm_mock.repo.get_default_skill_names = Mock(
            return_value=[
                ('default', ['time', 'weather']),
                ('test_platform', ['test_skill'])
            ]
        )
        self.msm_mock.skills_data = dict(
            skills=[
                dict(name='test_skill', beta=False)
            ]
        )
        skill = Mock()
        skill.is_local = True
        self.msm_mock.list_defaults.return_value = [skill]
        self.create_msm_mock.return_value = self.msm_mock

    def _mock_config(self):
        """Define a mock object representing the device configuration."""
        config_mgr_patch = patch(MOCK_PACKAGE + 'Configuration')
        self.addCleanup(config_mgr_patch.stop)
        self.config_mgr_mock = config_mgr_patch.start()
        get_config_mock = Mock()
        get_config_mock.return_value = self._build_config()
        self.config_mgr_mock.get = get_config_mock

    def _build_config(self):
        """Build a dictionary representing device configs needed to test."""
        return dict(
            skills=dict(
                msm=dict(
                    directory='skills',
                    versioned=True,
                    repo=dict(
                        cache='.skills-repo',
                        url='https://github.com/MycroftAI/mycroft-skills',
                        branch='19.02'
                    )
                ),
                update_interval=1.0,
                auto_update=False,
                blacklisted_skills=[],
                priority_skills=['foobar'],
                upload_skill_manifest=True
            ),
            data_dir=self.temp_dir
        )

    def _mock_connected(self):
        """Define a mock object representing the connected() function."""
        connected_patch = patch(MOCK_PACKAGE + 'connected')
        self.addCleanup(connected_patch.stop)
        self.connected_mock = connected_patch.start()
        self.connected_mock.return_value = True

    def _mock_dialog(self):
        """Define a mock object representing the dialog module."""
        dialog_patch = patch(MOCK_PACKAGE + 'dialog.get')
        self.addCleanup(dialog_patch.stop)
        self.dialog_mock = dialog_patch.start()

    def _mock_time(self):
        """Define a mock object representing the built-in time function.

        For the purposes of unit tests, we don't really care about the actual
        time.  To have the tests produce predictable results, we just need
        the time() function to return a value we can depend on.
        """
        time_patch = patch(MOCK_PACKAGE + 'time')
        self.addCleanup(time_patch.stop)
        self.time_mock = time_patch.start()
        self.time_mock.return_value = 100

    def tearDown(self):
        rmtree(self.temp_dir)

    def test_instantiate(self):
        """Test the results of instantiating the class."""
        updater = SkillUpdater(self.message_bus)
        self.assertEqual(updater.config['data_dir'], self.temp_dir)
        self.assertEqual(updater.update_interval, 3600)
        self.assertEqual(
            updater.dot_msm_path,
            path.join(self.temp_dir, '.msm')
        )
        self.assertFalse(path.exists(updater.dot_msm_path))
        self.assertLess(updater.next_download, time())

    def test_load_installed_skills(self):
        """Test loading a set of installed skills into an instance attribute"""
        skill_file_path = path.join(self.temp_dir, '.mycroft_skills')
        with open(skill_file_path, 'w') as skill_file:
            skill_file.write('FooSkill\n')
            skill_file.write('BarSkill\n')

        patch_path = MOCK_PACKAGE + 'SkillUpdater.installed_skills_file_path'
        with patch(patch_path, new_callable=PropertyMock) as mock_file_path:
            mock_file_path.return_value = skill_file_path
            updater = SkillUpdater(self.message_bus)
            updater._load_installed_skills()

        self.assertEqual({'FooSkill', 'BarSkill'}, updater.installed_skills)

    def test_apply_install_or_update(self):
        """Test invoking MSM to install or update skills"""
        skill = self._build_mock_msm_skill_list()
        self.msm_mock.list_defaults.return_value = [skill]
        updater = SkillUpdater(self.message_bus)
        updater._apply_install_or_update(quick=False)

        self.msm_mock.apply.assert_called_once_with(
            updater.install_or_update,
            self.msm_mock.list(),
            max_threads=2
        )

    def test_apply_install_or_update_quick(self):
        """Test invoking MSM to install or update skills quickly"""
        skill = self._build_mock_msm_skill_list()
        self.msm_mock.list_defaults.return_value = [skill]
        updater = SkillUpdater(self.message_bus)
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
        self.msm_mock.list_defaults.return_value = [skill]
        updater = SkillUpdater(self.message_bus)
        updater._apply_install_or_update(quick=True)

        self.msm_mock.apply.assert_called_once_with(
            updater.install_or_update,
            self.msm_mock.list(),
            max_threads=20
        )

    def test_save_installed_skills(self):
        """Test saving list of installed skills to a file."""
        skill_file_path = path.join(self.temp_dir, '.mycroft_skills')
        patch_path = MOCK_PACKAGE + 'SkillUpdater.installed_skills_file_path'
        with patch(patch_path, new_callable=PropertyMock) as mock_file:
            mock_file.return_value = skill_file_path
            updater = SkillUpdater(self.message_bus)
            updater.installed_skills = ['FooSkill', 'BarSkill']
            updater._save_installed_skills()

        with open(skill_file_path) as skill_file:
            skills = skill_file.readlines()

        self.assertListEqual(['FooSkill\n', 'BarSkill\n'], skills)

    def test_installed_skills_path_virtual_env(self):
        """Test the property representing the installed skill file path."""
        with patch(MOCK_PACKAGE + 'sys', spec=True) as sys_mock:
            sys_mock.executable = 'path/to/the/virtual_env/bin/python'
            with patch(MOCK_PACKAGE + 'os.access') as os_patch:
                os_patch.return_value = True
                updater = SkillUpdater(self.message_bus)
                self.assertEqual(
                    'path/to/the/virtual_env/.mycroft-skills',
                    updater.installed_skills_file_path
                )

    def test_installed_skills_path_not_virtual_env(self):
        """Test the property representing the installed skill file path."""
        with patch(MOCK_PACKAGE + 'os.access') as os_patch:
            os_patch.return_value = False
            updater = SkillUpdater(self.message_bus)
            self.assertEqual(
                path.expanduser('~/.mycroft/.mycroft-skills'),
                updater.installed_skills_file_path
            )

    def test_default_skill_names(self):
        """Test the property representing the list of default skills."""
        updater = SkillUpdater(self.message_bus)
        self.assertIn('time', updater.default_skill_names)
        self.assertIn('weather', updater.default_skill_names)
        self.assertIn('test_skill', updater.default_skill_names)

    def test_download_skills_not_connected(self):
        """Test the error that occurs when the device is not connected."""
        with patch(MOCK_PACKAGE + 'connected') as connected_mock:
            connected_mock.return_value = False
            with patch(MOCK_PACKAGE + 'time', spec=True) as time_mock:
                time_mock.return_value = 100
                with patch(MOCK_PACKAGE + 'dialog.get') as dialog_mock:
                    sm = SkillUpdater(self.message_bus)
                    result = sm.download_skills(speak=True)
                    dialog_mock.assert_called_once_with(
                        'not connected to the internet'
                    )

        self.assertFalse(result)
        self.assertListEqual(self.message_bus.message_types, ['speak'])
        self.assertEqual(400, sm.next_download)

    def test_post_manifest_allowed(self):
        """Test calling the skill manifest API endpoint"""
        self.msm_mock.skills_data = 'foo'
        with patch(MOCK_PACKAGE + 'is_paired') as paired_mock:
            paired_mock.return_value = True
            with patch(MOCK_PACKAGE + 'DeviceApi', spec=True) as api_mock:
                SkillUpdater(self.message_bus).post_manifest()
                api_instance = api_mock.return_value
                api_instance.upload_skills_data.assert_called_once_with('foo')
            paired_mock.assert_called_once()

    def test_get_skill_data(self):
        """Test invoking MSM to retrieve skill data."""
        updater = SkillUpdater(self.message_bus)
        skill_data = updater._get_skill_data('test_skill')
        self.assertDictEqual(dict(name='test_skill', beta=False), skill_data)

    def test_get_skill_data_not_found(self):
        """Test invoking MSM to retrieve unknown skill data."""
        updater = SkillUpdater(self.message_bus)
        skill_data = updater._get_skill_data('foo')
        self.assertDictEqual({}, skill_data)

    def test_install_or_update_beta(self):
        """Test calling install_or_update with a beta skill."""
        self.msm_mock.skills_data['skills'][0]['beta'] = True
        skill = self._build_mock_msm_skill_list()
        skill.is_local = False
        updater = SkillUpdater(self.message_bus)
        updater.install_or_update(skill)
        self.assertIn('foobar', updater.installed_skills)
        self.assertIsNone(skill.sha)

    def test_install_or_update_local(self):
        """Test calling install_or_update with a local skill"""
        skill = self._build_mock_msm_skill_list()
        updater = SkillUpdater(self.message_bus)
        updater.install_or_update(skill)
        self.assertIn('foobar', updater.installed_skills)
        skill.update.assert_called_once()
        skill.update_deps.assert_called_once()
        self.msm_mock.install.assert_not_called()

    def test_install_or_update_default(self):
        """Test calling install_or_update with a default skill"""
        skill = self._build_mock_msm_skill_list()
        skill.name = 'test_skill'
        skill.is_local = False
        updater = SkillUpdater(self.message_bus)
        updater.install_or_update(skill)
        self.assertIn('test_skill', updater.installed_skills)
        skill.update.assert_not_once()
        self.msm_mock.install.assert_called_once_with(skill, origin='default')

    def test_install_or_update_default_fail(self):
        """Test calling install_or_update with a failed install result"""
        skill = self._build_mock_msm_skill_list()
        skill.name = 'test_skill'
        skill.is_local = False
        self.msm_mock.install.side_effect = ValueError
        updater = SkillUpdater(self.message_bus)
        with self.assertRaises(ValueError):
            updater.install_or_update(skill)
        self.assertNotIn('test_skill', updater.installed_skills)
        skill.update.assert_not_once()
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
        skill.path = path.join(self.temp_dir, 'foobar')

        return skill

    def test_speak_skill_updated(self):
        """Test emitting a speak event to the bus when skills are updated."""
        SkillUpdater(self.message_bus)._speak_skill_updated(speak=True)
        self.dialog_mock.assert_called_once_with('skills updated')
        self.assertListEqual(['speak'], self.message_bus.message_types)

    def test_schedule_retry(self):
        """Test scheduling a retry of a failed install."""
        updater = SkillUpdater(self.message_bus)
        updater._schedule_retry()
        self.assertEqual(1, updater.install_retries)
        self.assertEqual(400, updater.next_download)
        self.assertFalse(updater.default_skill_install_error)

    def test_update_download_time(self):
        """Test updating the next time a download will occur."""
        dot_msm_path = path.join(self.temp_dir, '.msm')
        Path(dot_msm_path).touch()
        dot_msm_mtime_before = path.getmtime(dot_msm_path)
        sleep(0.5)
        SkillUpdater(self.message_bus)._update_download_time()
        dot_msm_mtime_after = path.getmtime(path.join(self.temp_dir, '.msm'))
        self.assertLess(dot_msm_mtime_before, dot_msm_mtime_after)
