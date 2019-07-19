import tempfile
from os import path
from shutil import rmtree
from time import time
from unittest import TestCase
from unittest.mock import Mock, patch

from mycroft.skills.skill_manager import SkillManager


class MockMessageBus(object):
    def __init__(self):
        self.message_types = []
        self.message_data = []
        self.event_handlers = []

    def emit(self, message):
        self.message_types.append(message.type)
        self.message_data.append(message.data)

    def on(self, event, _):
        self.event_handlers.append(event)


class MycroftSkillTest(TestCase):
    def setUp(self):
        self.message_bus = MockMessageBus()
        self.temp_dir = tempfile.mkdtemp()
        self._mock_msm()
        self._mock_config()

    def _mock_msm(self):
        msm_patch = patch('mycroft.skills.skill_manager.msm_creator')
        self.create_msm_mock = msm_patch.start()
        msm_mock = Mock()
        msm_mock.skills_dir = self.temp_dir
        self.create_msm_mock.return_value = msm_mock
        self.addCleanup(msm_patch.stop)

    def _mock_config(self):
        config_mgr_patch = patch('mycroft.skills.skill_manager.Configuration')
        self.config_mgr_mock = config_mgr_patch.start()
        get_config_mock = Mock()
        get_config_mock.return_value = self._build_config()
        self.config_mgr_mock.get = get_config_mock
        self.addCleanup(config_mgr_patch.stop)

    def _build_config(self):
        config = dict(
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
                priority_skills=['mycroft-pairing']
            ),
            data_dir=self.temp_dir
        )

        return config

    def test_instantiate(self):
        sm = SkillManager(self.message_bus)
        self.assertEquals(sm.config['data_dir'], self.temp_dir)
        self.assertEquals(sm.update_interval, 3600)
        self.assertEquals(sm.dot_msm, path.join(self.temp_dir, '.msm'))
        self.assertFalse(path.exists(sm.dot_msm))
        self.assertIsNone(sm.last_download)
        self.assertLess(sm.next_download, time())
        expected_result = [
            'skill.converse.request',
            'mycroft.internet.connected',
            'skillmanager.update',
            'skillmanager.list',
            'skillmanager.deactivate',
            'skillmanager.keep',
            'skillmanager.activate',
            'mycroft.paired'
        ]
        self.assertListEqual(expected_result, self.message_bus.event_handlers)

    def tearDown(self):
        rmtree(self.temp_dir)
