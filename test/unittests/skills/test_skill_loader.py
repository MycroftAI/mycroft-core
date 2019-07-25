from time import time
from unittest.mock import Mock, patch

from mycroft.skills.skill_loader import _get_last_modified_date, SkillLoader
from ..base import MycroftUnitTestBase

ONE_MINUTE = 60


class TestSkillLoader(MycroftUnitTestBase):
    mock_package = 'mycroft.skills.skill_loader.'

    def setUp(self):
        super().setUp()
        self.skill = {}
        self.skill_directory = self._load_skill_directory()
        self.loader = SkillLoader(
            self.message_bus_mock,
            str(self.skill_directory),
            self.skill
        )
        self._mock_load_skill()

    def _load_skill_directory(self):
        skill_directory = self.temp_dir.joinpath('test_skill')
        skill_directory.mkdir()
        for file_name in ('foo.txt', 'bar.py', '.foobar', 'bar.pyc'):
            skill_directory.joinpath(file_name).touch()

        return skill_directory

    def _mock_load_skill(self):
        load_skill_patch = patch(self.mock_package + 'load_skill')
        self.addCleanup(load_skill_patch.stop)
        self.load_skill_mock = load_skill_patch.start()

    def test_get_last_modified_date(self):
        last_modified_date = _get_last_modified_date(str(self.skill_directory))
        file_path = self.skill_directory.joinpath('bar.py')
        expected_result = file_path.stat().st_mtime
        self.assertEqual(last_modified_date, expected_result)

    def test_instantiate(self):
        """Test class instantiation results

        Every test will instantiate SkillLoader; check instantiation
        results once.
        """
        self.assertEqual(self.message_bus_mock, self.loader.bus)
        self.assertEqual(
            str(self.skill_directory),
            self.loader.skill_directory
        )
        self.assertDictEqual(
            dict(
                id='test_skill',
                path=str(self.skill_directory),
                loaded=False
            ),
            self.loader.skill
        )
        self.assertEqual(
            self.skill_directory.joinpath('bar.py').stat().st_mtime,
            self.loader.directory_last_modified
        )
        self.assertFalse(self.loader.skill_was_loaded)
        self.assertEqual(self.config_mgr_mock.get(), self.loader.config)

    def test_skill_already_loaded(self):
        skill_instance = Mock()
        skill_instance.reload_skill = True
        skill_instance.default_shutdown = Mock()
        self.loader.skill.update(
            loaded=True,
            instance=skill_instance,
            last_modified=time() + ONE_MINUTE
        )
        self.assertFalse(self.loader.do_reload)
        self.assertFalse(self.loader.do_load)
        self.assertFalse(self.loader.reload_blocked)
        self.loader.load()
        self.assertListEqual([], self.message_bus_mock.message_types)
        self.assertFalse(self.loader.skill_was_loaded)
        skill_instance.default_shutdown.assert_not_called()
        self.load_skill_mock.assert_not_called()

    def test_skill_reloading_blocked(self):
        skill_instance = Mock()
        skill_instance.reload_skill = False
        self.loader.skill.update(
            active=False,
            loaded=True,
            instance=skill_instance
        )
        self.assertTrue(self.loader.do_reload)
        self.assertFalse(self.loader.do_load)
        self.assertTrue(self.loader.reload_blocked)
        self.loader.load()
        self.assertFalse(self.loader.skill_was_loaded)
        skill_instance.default_shutdown.assert_not_called()
        self.load_skill_mock.assert_not_called()

    def test_skill_reload(self):
        skill_instance = Mock()
        skill_instance.name = 'TestSkill'
        skill_instance.reload_skill = True
        skill_instance.default_shutdown = Mock()
        self.loader.skill.update(
            active=True,
            loaded=True,
            last_modified=0,
            instance=skill_instance,
            id='test_skill'
        )
        self.load_skill_mock.return_value = skill_instance
        self.assertTrue(self.loader.do_reload)
        self.assertFalse(self.loader.do_load)
        self.assertFalse(self.loader.reload_blocked)
        with patch(self.mock_package + 'create_skill_descriptor') as csd_mock:
            self.loader.load()
            csd_mock.assert_called_once_with(str(self.skill_directory))
            self.load_skill_mock.assert_called_once_with(
                csd_mock.return_value,
                self.message_bus_mock,
                'test_skill',
                []
            )
        self.assertTrue(self.loader.skill_was_loaded)
        self.assertTrue(self.loader.skill['loaded'])
        self.assertEqual(
            self.loader.skill['last_modified'],
            self.loader.directory_last_modified
        )
        skill_instance.default_shutdown.assert_called_once()
        self.assertIn(
            'mycroft.skills.shutdown',
            self.message_bus_mock.message_types
        )
        self.assertIn(
            'mycroft.skills.loaded',
            self.message_bus_mock.message_types
        )

    def test_skill_load(self):
        skill_instance = Mock()
        skill_instance.name = 'TestSkill'
        skill_instance.reload_skill = True
        skill_instance.default_shutdown = Mock()
        self.loader.skill.update(
            active=True,
            loaded=False,
            id='test_skill'
        )
        self.load_skill_mock.return_value = skill_instance
        self.assertFalse(self.loader.do_reload)
        self.assertTrue(self.loader.do_load)
        self.assertFalse(self.loader.reload_blocked)
        with patch(self.mock_package + 'create_skill_descriptor') as csd_mock:
            self.loader.load()
            csd_mock.assert_called_once_with(str(self.skill_directory))
            self.load_skill_mock.assert_called_once_with(
                csd_mock.return_value,
                self.message_bus_mock,
                'test_skill',
                []
            )
        self.assertTrue(self.loader.skill_was_loaded)
        self.assertTrue(self.loader.skill['loaded'])
        self.assertEqual(
            self.loader.skill['last_modified'],
            self.loader.directory_last_modified
        )
        skill_instance.default_shutdown.assert_not_called()
        self.assertListEqual(
            ['mycroft.skills.loaded'],
            self.message_bus_mock.message_types
        )

    def test_skill_load_failure(self):
        self.load_skill_mock.return_value = None
        self.assertFalse(self.loader.do_reload)
        self.assertTrue(self.loader.do_load)
        self.assertFalse(self.loader.reload_blocked)
        with patch(self.mock_package + 'create_skill_descriptor') as csd_mock:
            self.loader.load()
            csd_mock.assert_called_once_with(str(self.skill_directory))
            self.load_skill_mock.assert_called_once_with(
                csd_mock.return_value,
                self.message_bus_mock,
                'test_skill',
                []
            )
        self.assertFalse(self.loader.skill_was_loaded)
        self.assertFalse(self.loader.skill['loaded'])
        self.assertListEqual(
            ['mycroft.skills.loading_failure'],
            self.message_bus_mock.message_types
        )
