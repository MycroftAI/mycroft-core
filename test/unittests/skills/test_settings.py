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
import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import call, Mock, patch

from mycroft.skills.settings import (
    get_local_settings,
    save_settings,
    SkillSettingsDownloader,
    SettingsMetaUploader
)
from ..base import MycroftUnitTestBase


class TestSettingsMetaUploader(MycroftUnitTestBase):
    use_msm_mock = True
    mock_package = 'mycroft.skills.settings.'

    def setUp(self):
        super().setUp()
        self.uploader = SettingsMetaUploader(str(self.temp_dir), 'test_skill')
        self.uploader.api = Mock()
        self.is_paired_mock = self._mock_is_paired()
        self.timer_mock = self._mock_timer()
        self.skill_metadata = dict(
            skillMetadata=dict(
                sections=[
                    dict(
                        name='Test Section',
                        fields=[dict(type='label', label='Test Field')]
                    )
                ]
            )
        )

    def _mock_is_paired(self):
        is_paired_patch = patch(self.mock_package + 'is_paired')
        self.addCleanup(is_paired_patch.stop)
        is_paired_mock = is_paired_patch.start()
        is_paired_mock.return_value = True

        return is_paired_mock

    def _mock_timer(self):
        timer_patch = patch(self.mock_package + 'Timer')
        self.addCleanup(timer_patch.stop)
        timer_mock = timer_patch.start()

        return timer_mock

    def test_not_paired(self):
        self.is_paired_mock.return_value = False
        self.uploader.upload()
        self._check_api_not_called()
        self._check_timer_called()

    @patch('mycroft.skills.settings.DeviceApi')
    def test_no_settingsmeta(self, mock_api):
        api_instance = Mock()
        api_instance.identity.uuid = '42'
        mock_api.return_value = api_instance

        self.uploader.upload()
        self._check_settingsmeta()
        self._check_api_call()
        self._check_timer_not_called()

    @patch('mycroft.skills.settings.DeviceApi')
    def test_failed_upload(self, mock_api):
        """The API call to upload the settingsmeta fails.

        This will cause a timer to be generated to retry the update.
        """
        api_instance = Mock()
        api_instance.identity.uuid = '42'
        api_instance.upload_skill_metadata = Mock(side_effect=ValueError)
        mock_api.return_value = api_instance
        self.uploader.upload()
        self._check_settingsmeta()
        self._check_api_call()
        self._check_timer_called()

    @patch('mycroft.skills.settings.DeviceApi')
    def test_json_settingsmeta(self, mock_api):
        api_instance = Mock()
        api_instance.identity.uuid = '42'
        mock_api.return_value = api_instance

        json_path = str(self.temp_dir.joinpath('settingsmeta.json'))
        with open(json_path, 'w') as json_file:
            json.dump(self.skill_metadata, json_file)

        self.uploader.upload()
        self._check_settingsmeta(self.skill_metadata)
        self._check_api_call()
        self._check_timer_not_called()

    @patch('mycroft.skills.settings.DeviceApi')
    def test_yaml_settingsmeta(self, mock_api):
        api_instance = Mock()
        api_instance.identity.uuid = '42'
        mock_api.return_value = api_instance

        skill_metadata = (
            'skillMetadata:\n  sections:\n    - name: "Test Section"\n      '
            'fields:\n      - type: "label"\n        label: "Test Field"'
        )
        yaml_path = str(self.temp_dir.joinpath('settingsmeta.yaml'))
        with open(yaml_path, 'w') as yaml_file:
            yaml_file.write(skill_metadata)

        self.uploader.upload()
        self._check_settingsmeta(self.skill_metadata)
        self._check_api_call()
        self._check_timer_not_called()

    def _check_settingsmeta(self, skill_settings=None):
        expected_settings_meta = dict(
            skill_gid='test_skill|99.99',
            display_name='Test Skill',
        )
        if skill_settings is not None:
            expected_settings_meta.update(skill_settings)

        self.assertDictEqual(
            expected_settings_meta,
            self.uploader.settings_meta
        )

    def _check_api_call(self):
        self.assertListEqual(
            [call.upload_skill_metadata(self.uploader.settings_meta)],
            self.uploader.api.method_calls
        )

    def _check_api_not_called(self):
        self.assertListEqual([], self.uploader.api.method_calls)

    def _check_timer_called(self):
        self.assertListEqual(
            [call.start()],
            self.timer_mock.return_value.method_calls
        )

    def _check_timer_not_called(self):
        self.assertListEqual([], self.timer_mock.return_value.method_calls)


class TestSettingsDownloader(MycroftUnitTestBase):
    mock_package = 'mycroft.skills.settings.'

    def setUp(self):
        super().setUp()
        self.settings_path = self.temp_dir.joinpath('settings.json')
        self.downloader = SkillSettingsDownloader(self.message_bus_mock)
        self.downloader.api = Mock()
        self.is_paired_mock = self._mock_is_paired()
        self.timer_mock = self._mock_timer()

    def _mock_is_paired(self):
        is_paired_patch = patch(self.mock_package + 'is_paired')
        self.addCleanup(is_paired_patch.stop)
        is_paired_mock = is_paired_patch.start()
        is_paired_mock.return_value = True

        return is_paired_mock

    def _mock_timer(self):
        timer_patch = patch(self.mock_package + 'Timer')
        self.addCleanup(timer_patch.stop)
        timer_mock = timer_patch.start()

        return timer_mock

    def test_not_paired(self):
        self.is_paired_mock.return_value = False
        self.downloader.download()
        self._check_api_not_called()
        self._check_timer_called()

    def test_settings_not_changed(self):
        test_skill_settings = {
            'test_skill|99.99': {"test_setting": 'test_value'}
        }
        self.downloader.last_download_result = test_skill_settings
        self.downloader.api.get_skill_settings = Mock(
            return_value=test_skill_settings)
        self.downloader.download()
        self._check_api_called()
        self._check_timer_called()
        self._check_no_message_bus_events()

    def test_settings_changed(self):
        local_skill_settings = {
            'test_skill|99.99': {"test_setting": 'test_value'}
        }
        remote_skill_settings = {
            'test_skill|99.99': {"test_setting": 'foo'}
        }
        self.downloader.last_download_result = local_skill_settings
        self.downloader.api.get_skill_settings = Mock(
            return_value=remote_skill_settings)
        self.downloader.download()
        self._check_api_called()
        self._check_timer_called()
        self._check_message_bus_events(remote_skill_settings)

    def test_download_failed(self):
        self.downloader.api.get_skill_settings = Mock(side_effect=ValueError)
        pre_download_local_settings = {
            'test_skill|99.99': {"test_setting": 'test_value'}
        }
        self.downloader.last_download_result = pre_download_local_settings
        self.downloader.download()
        self._check_api_called()
        self._check_timer_called()
        self._check_no_message_bus_events()
        self.assertEqual(
            pre_download_local_settings,
            self.downloader.last_download_result
        )

    def test_stop_downloading(self):
        """Ensure that the timer is cancelled and the continue flag is lowered.
        """
        self.is_paired_mock.return_value = False  # Skip all the download logic
        self.downloader.download()  # Start downloading creates the timer
        self.downloader.stop_downloading()
        self.assertFalse(self.downloader.continue_downloading)
        self.assertTrue(
            self.downloader.download_timer.cancel.called_once_with())

    def _check_api_called(self):
        self.assertListEqual(
            [call.get_skill_settings()],
            self.downloader.api.method_calls
        )

    def _check_api_not_called(self):
        self.assertListEqual([], self.downloader.api.method_calls)

    def _check_timer_called(self):
        self.assertListEqual(
            [call.start()],
            self.timer_mock.return_value.method_calls
        )

    def _check_no_message_bus_events(self):
        self.assertListEqual(self.message_bus_mock.message_types, [])
        self.assertListEqual(self.message_bus_mock.message_data, [])

    def _check_message_bus_events(self, remote_skill_settings):
        self.assertListEqual(
            ['mycroft.skills.settings.changed'],
            self.message_bus_mock.message_types
        )
        self.assertListEqual(
            [remote_skill_settings],
            self.message_bus_mock.message_data
        )


class TestSettings(TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.mkdtemp()
        self.temp_dir = Path(temp_dir)
        self.skill_mock = Mock()
        self.skill_mock.root_dir = str(self.temp_dir)
        self.skill_mock.name = 'test_skill'

    def test_empty_settings(self):
        settings = get_local_settings(
            self.skill_mock.root_dir,
            self.skill_mock.name
        )
        self.assertDictEqual(settings, {})

    def test_settings_file_exists(self):
        settings_path = str(self.temp_dir.joinpath('settings.json'))
        with open(settings_path, 'w') as settings_file:
            settings_file.write('{"foo": "bar"}\n')

        settings = get_local_settings(
            self.skill_mock.root_dir,
            self.skill_mock.name
        )
        self.assertDictEqual(settings, {'foo': 'bar'})
        self.assertEqual(settings['foo'], 'bar')
        self.assertNotIn('store', settings)
        self.assertIn('foo', settings)

    def test_store_settings(self):
        settings = dict(foo='bar')
        save_settings(self.skill_mock.root_dir, settings)
        settings_path = str(self.temp_dir.joinpath('settings.json'))
        with open(settings_path) as settings_file:
            file_contents = settings_file.read()

        self.assertEqual(file_contents, '{"foo": "bar"}')
