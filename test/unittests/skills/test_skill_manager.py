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
from unittest import TestCase
from unittest.mock import Mock, patch

from mycroft.skills.skill_loader import SkillLoader
from mycroft.skills.skill_manager import SkillManager, UploadQueue
from ..base import MycroftUnitTestBase


class TestUploadQueue(TestCase):

    def test_upload_queue_create(self):
        queue = UploadQueue()
        self.assertFalse(queue.started)
        queue.start()
        self.assertTrue(queue.started)

    def test_upload_queue_use(self):
        queue = UploadQueue()
        queue.start()
        specific_loader = Mock(spec=SkillLoader, instance=Mock())
        loaders = [Mock(), specific_loader, Mock(), Mock()]
        # Check that putting items on the queue makes it longer
        for i, l in enumerate(loaders):
            queue.put(l)
            self.assertEqual(len(queue), i + 1)
        # Check that adding an existing item replaces that item
        queue.put(specific_loader)
        self.assertEqual(len(queue), len(loaders))
        # Check that sending items empties the queue
        queue.send()
        self.assertEqual(len(queue), 0)

    def test_upload_queue_preloaded(self):
        queue = UploadQueue()
        loaders = [Mock(), Mock(), Mock(), Mock()]
        for i, l in enumerate(loaders):
            queue.put(l)
            self.assertEqual(len(queue), i + 1)
        # Check that starting the queue will send all the items in the queue
        queue.start()
        self.assertEqual(len(queue), 0)
        for l in loaders:
            l.instance.settings_meta.upload.assert_called_once_with()


class TestSkillManager(MycroftUnitTestBase):
    mock_package = 'mycroft.skills.skill_manager.'

    def setUp(self):
        super().setUp()
        self._mock_skill_updater()
        self._mock_skill_settings_downloader()
        self.skill_manager = SkillManager(self.message_bus_mock)
        self._mock_skill_loader_instance()

    def _mock_skill_settings_downloader(self):
        settings_download_patch = patch(
            self.mock_package + 'SkillSettingsDownloader',
            spec=True
        )
        self.addCleanup(settings_download_patch.stop)
        self.settings_download_mock = settings_download_patch.start()

    def _mock_skill_updater(self):
        skill_updater_patch = patch(
            self.mock_package + 'SkillUpdater',
            spec=True
        )
        self.addCleanup(skill_updater_patch.stop)
        self.skill_updater_mock = skill_updater_patch.start()

    def _mock_skill_loader_instance(self):
        self.skill_dir = self.temp_dir.joinpath('test_skill')
        self.skill_loader_mock = Mock(spec=SkillLoader)
        self.skill_loader_mock.instance = Mock()
        self.skill_loader_mock.instance.default_shutdown = Mock()
        self.skill_loader_mock.instance.converse = Mock()
        self.skill_loader_mock.instance.converse.return_value = True
        self.skill_loader_mock.skill_id = 'test_skill'
        self.skill_manager.skill_loaders = {
            str(self.skill_dir): self.skill_loader_mock
        }

    def test_instantiate(self):
        self.assertEqual(
            self.skill_manager.config['data_dir'],
            str(self.temp_dir)
        )
        expected_result = [
            'mycroft.internet.connected',
            'skillmanager.list',
            'skillmanager.deactivate',
            'skillmanager.keep',
            'skillmanager.activate',
            'mycroft.paired',
            'mycroft.skills.settings.update',
            'mycroft.skills.initialized',
            'mycroft.skills.trained',
            'mycroft.skills.is_alive',
            'mycroft.skills.is_ready',
            'mycroft.skills.all_loaded'
        ]
        self.assertListEqual(
            expected_result,
            self.message_bus_mock.event_handlers
        )

    def test_unload_removed_skills(self):
        self.skill_manager._unload_removed_skills()

        self.assertDictEqual({}, self.skill_manager.skill_loaders)
        self.skill_loader_mock.unload.assert_called_once_with()

    def test_send_skill_list(self):
        self.skill_loader_mock.active = True
        self.skill_loader_mock.loaded = True
        self.skill_manager.send_skill_list(None)

        self.assertListEqual(
            ['mycroft.skills.list'],
            self.message_bus_mock.message_types
        )
        message_data = self.message_bus_mock.message_data[0]
        self.assertIn('test_skill', message_data.keys())
        skill_data = message_data['test_skill']
        self.assertDictEqual(dict(active=True, id='test_skill'), skill_data)

    def test_stop(self):
        self.skill_manager.stop()

        self.assertTrue(self.skill_manager._stop_event.is_set())
        instance = self.skill_loader_mock.instance
        instance.default_shutdown.assert_called_once_with()

    def test_handle_paired(self):
        self.skill_updater_mock.next_download = 0
        self.skill_manager.handle_paired(None)
        updater = self.skill_manager.skill_updater
        updater.post_manifest.assert_called_once_with(
            reload_skills_manifest=True)

    def test_deactivate_skill(self):
        message = Mock()
        message.data = dict(skill='test_skill')
        self.skill_manager.deactivate_skill(message)
        self.skill_loader_mock.deactivate.assert_called_once_with()

    def test_deactivate_except(self):
        message = Mock()
        message.data = dict(skill='test_skill')
        self.skill_loader_mock.active = True
        foo_skill_loader = Mock(spec=SkillLoader)
        foo_skill_loader.skill_id = 'foo'
        foo2_skill_loader = Mock(spec=SkillLoader)
        foo2_skill_loader.skill_id = 'foo2'
        test_skill_loader = Mock(spec=SkillLoader)
        test_skill_loader.skill_id = 'test_skill'
        self.skill_manager.skill_loaders['foo'] = foo_skill_loader
        self.skill_manager.skill_loaders['foo2'] = foo2_skill_loader
        self.skill_manager.skill_loaders['test_skill'] = test_skill_loader

        self.skill_manager.deactivate_except(message)
        foo_skill_loader.deactivate.assert_called_once_with()
        foo2_skill_loader.deactivate.assert_called_once_with()
        self.assertFalse(test_skill_loader.deactivate.called)

    def test_activate_skill(self):
        message = Mock()
        message.data = dict(skill='test_skill')
        test_skill_loader = Mock(spec=SkillLoader)
        test_skill_loader.skill_id = 'test_skill'
        test_skill_loader.active = False

        self.skill_manager.skill_loaders = {}
        self.skill_manager.skill_loaders['test_skill'] = test_skill_loader

        self.skill_manager.activate_skill(message)
        test_skill_loader.activate.assert_called_once_with()

    def test_reload_modified(self):
        self.skill_dir.mkdir(parents=True)
        self.skill_dir.joinpath('__init__.py').touch()
        self.skill_loader_mock.reload_needed.return_value = True
        self.skill_manager._reload_modified_skills()
        self.skill_loader_mock.reload.assert_called_once_with()
        self.assertEqual(
            self.skill_loader_mock,
            self.skill_manager.skill_loaders[str(self.skill_dir)]
        )
