from os import path
from unittest.mock import Mock, patch

from mycroft.skills.skill_manager import SkillManager
from ..base import MycroftUnitTestBase
from ..mocks import mock_msm


class TestSkillManager(MycroftUnitTestBase):
    mock_package = 'mycroft.skills.skill_manager.'
    use_msm_mock = True

    def setUp(self):
        super().setUp()
        self._mock_skill_updater()

    def _mock_msm(self):
        if self.use_msm_mock:
            msm_patch = patch(self.mock_package + 'msm_creator')
            self.addCleanup(msm_patch.stop)
            self.create_msm_mock = msm_patch.start()
            self.msm_mock = mock_msm(str(self.temp_dir))
            self.create_msm_mock.return_value = self.msm_mock

    def _mock_skill_updater(self):
        skill_updater_patch = patch(
            self.mock_package + 'SkillUpdater',
            spec=True
        )
        self.addCleanup(skill_updater_patch.stop)
        self.skill_updater_mock = skill_updater_patch.start()

    def test_instantiate(self):
        manager = SkillManager(self.message_bus_mock)
        self.assertEqual(manager.config['data_dir'], str(self.temp_dir))
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
        self.assertListEqual(
            expected_result,
            self.message_bus_mock.event_handlers
        )

    def test_remove_git_locks(self):
        git_dir = self.temp_dir.joinpath('foo/.git')
        git_dir.mkdir(parents=True)
        git_lock_file_path = str(git_dir.joinpath('index.lock'))
        with open(git_lock_file_path, 'w') as git_lock_file:
            git_lock_file.write('foo')

        SkillManager(self.message_bus_mock)._remove_git_locks()

        self.assertFalse(path.exists(git_lock_file_path))

    def test_load_priority(self):
        manager = SkillManager(self.message_bus_mock)
        load_mock = Mock()
        manager._load_skill = load_mock
        skill, manager.msm.list = self._build_mock_msm_skill_list()
        manager.load_priority()

        self.assertFalse(skill.install.called)
        load_mock.assert_called_once_with(skill.path)

    def test_install_priority(self):
        manager = SkillManager(self.message_bus_mock)
        load_mock = Mock()
        manager._load_skill = load_mock
        skill, manager.msm.list = self._build_mock_msm_skill_list()
        skill.is_local = False
        manager.load_priority()

        self.assertTrue(skill.install.called)
        load_mock.assert_called_once_with(skill.path)

    def test_priority_skill_not_recognized(self):
        sm = SkillManager(self.message_bus_mock)
        load_or_reload_mock = Mock()
        sm._load_or_reload_skill = load_or_reload_mock
        skill, sm.msm.list = self._build_mock_msm_skill_list()
        skill.name = 'barfoo'
        sm.load_priority()

        self.assertFalse(skill.install.called)
        self.assertFalse(load_or_reload_mock.called)

    def test_priority_skill_install_failed(self):
        sm = SkillManager(self.message_bus_mock)
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
        skill.path = str(self.temp_dir.joinpath('foobar'))
        skill_list_func = Mock(return_value=[skill])

        return skill, skill_list_func

    # def test_no_skill_in_skill_dir(self):
    #     skill_dir = str(self.temp_dir.joinpath('path/to/skill/test_skill'))
    #     makedirs(skill_dir)
    #     manager = SkillManager(self.message_bus_mock)
    #     manager.skill_loaders = {skill_dir: {}}
    #     skill_loading = manager._load_or_reload_skill(skill_dir)
    #     self.assertFalse(skill_loading)
    #     self.assertDictEqual(
    #         dict(id='test_skill', path=skill_dir),
    #         manager.skill_loaders[skill_dir]
    #     )
