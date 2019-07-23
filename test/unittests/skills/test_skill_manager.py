import tempfile
from os import makedirs, path
from shutil import rmtree
from time import time
from unittest import TestCase
from unittest.mock import Mock, patch, PropertyMock

from msm import MycroftSkillsManager
from msm.skill_repo import SkillRepo
from msm.util import MsmProcessLock
from pathlib import Path

from mycroft.skills.skill_manager import _get_last_modified_date, SkillManager

MOCK_PACKAGE = 'mycroft.skills.skill_manager.'


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


class MycroftSkillTest(TestCase):
    def setUp(self):
        self.message_bus = MockMessageBus()
        self.temp_dir = tempfile.mkdtemp()
        self._mock_msm()
        self._mock_config()
        self._mock_skill_updater()

    def _mock_msm(self):
        msm_patch = patch(MOCK_PACKAGE + 'msm_creator')
        self.addCleanup(msm_patch.stop)
        self.create_msm_mock = msm_patch.start()
        self.msm_mock = Mock(spec=MycroftSkillsManager)
        self.msm_mock.skills_dir = self.temp_dir
        self.msm_mock.platform = 'test_platform'
        self.msm_mock.lock = MsmProcessLock()
        self.msm_mock.repo = Mock(spec=SkillRepo)
        self.msm_mock.repo.get_default_skill_names = Mock(return_value=[
            ('default', ['time', 'weather']),
            ('test_platform', ['test_skill'])
        ])
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
        config_mgr_patch = patch(MOCK_PACKAGE + 'Configuration')
        self.addCleanup(config_mgr_patch.stop)
        self.config_mgr_mock = config_mgr_patch.start()
        get_config_mock = Mock()
        get_config_mock.return_value = self._build_config()
        self.config_mgr_mock.get = get_config_mock

    def _mock_skill_updater(self):
        skill_updater_patch = patch(MOCK_PACKAGE + 'SkillUpdater', spec=True)
        self.addCleanup(skill_updater_patch.stop)
        self.skill_updater_mock = skill_updater_patch.start()

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
                priority_skills=['foobar'],
                upload_skill_manifest=True
            ),
            data_dir=self.temp_dir
        )

        return config

    def tearDown(self):
        rmtree(self.temp_dir)

    def test_get_last_modified_date(self):
        for file_name in ('foo.txt', 'bar.py', '.foobar', 'bar.pyc'):
            file_path = path.join(self.temp_dir, file_name)
            Path(file_path).touch()
        last_modified_date = _get_last_modified_date(self.temp_dir)
        expected_result = path.getmtime(path.join(self.temp_dir, 'bar.py'))
        self.assertEqual(last_modified_date, expected_result)

    def test_instantiate(self):
        sm = SkillManager(self.message_bus)
        self.assertEqual(sm.config['data_dir'], self.temp_dir)
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

    def test_remove_git_locks(self):
        git_dir = path.join(self.temp_dir, 'foo/.git')
        git_lock_file_path = path.join(git_dir, 'index.lock')
        makedirs(git_dir)
        with open(git_lock_file_path, 'w') as git_lock_file:
            git_lock_file.write('foo')

        SkillManager(self.message_bus)._remove_git_locks()

        self.assertFalse(path.exists(git_lock_file_path))

    def test_load_priority(self):
        sm = SkillManager(self.message_bus)
        load_or_reload_mock = Mock()
        sm._load_or_reload_skill = load_or_reload_mock
        skill, sm.msm.list = self._build_mock_msm_skill_list()
        sm.load_priority()

        self.assertFalse(skill.install.called)
        load_or_reload_mock.assert_called_once_with(skill.path)

    def test_install_priority(self):
        sm = SkillManager(self.message_bus)
        load_or_reload_mock = Mock()
        sm._load_or_reload_skill = load_or_reload_mock
        skill, sm.msm.list = self._build_mock_msm_skill_list()
        skill.is_local = False
        sm.load_priority()

        self.assertTrue(skill.install.called)
        load_or_reload_mock.assert_called_once_with(skill.path)

    def test_priority_skill_not_recognized(self):
        sm = SkillManager(self.message_bus)
        load_or_reload_mock = Mock()
        sm._load_or_reload_skill = load_or_reload_mock
        skill, sm.msm.list = self._build_mock_msm_skill_list()
        skill.name = 'barfoo'
        sm.load_priority()

        self.assertFalse(skill.install.called)
        self.assertFalse(load_or_reload_mock.called)

    def test_priority_skill_install_failed(self):
        sm = SkillManager(self.message_bus)
        load_or_reload_mock = Mock()
        sm._load_or_reload_skill = load_or_reload_mock
        skill, sm.msm.list = self._build_mock_msm_skill_list()
        skill.is_local = False
        skill.install.side_effect = ValueError
        sm.load_priority()

        self.assertRaises(ValueError, skill.install)
        self.assertFalse(load_or_reload_mock.called)

    def _build_mock_msm_skill_list(self):
        skill = Mock()
        skill.name = 'foobar'
        skill.is_local = True
        skill.install = Mock()
        skill.update = Mock()
        skill.update_deps = Mock()
        skill.path = path.join(self.temp_dir, 'foobar')
        skill_list_func = Mock(return_value=[skill])

        return skill, skill_list_func
