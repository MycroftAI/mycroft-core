from time import time
from unittest.mock import Mock, patch

from mycroft.skills.skill_loader import _get_last_modified_date, SkillLoader
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
        self.assertFalse(self.loader.load_attempted)
        self.assertFalse(self.loader.loaded)
        self.assertEqual(0, self.loader.last_modified)
        self.assertEqual(0, self.loader.last_loaded)
        self.assertIsNone(self.loader.instance)
        self.assertTrue(self.loader.active)
        self.assertFalse(self.loader.load_attempted)
        self.assertEqual(self.config_mgr_mock.get(), self.loader.config)

    def test_skill_already_loaded(self):
        self._build_skill_instance_mock()
        self.loader.loaded = True
        self.loader.last_loaded = time() + ONE_MINUTE
        self.loader.load()

        self.assertFalse(self.loader.load_attempted)
        self.loader.instance.default_shutdown.assert_not_called()
        self.load_skill_mock.assert_not_called()
        self.assertListEqual([], self.message_bus_mock.message_types)

    def test_skill_reloading_blocked(self):
        self._build_skill_instance_mock()
        self.loader.instance.reload_skill = False
        self.loader.active = False
        self.loader.loaded = True
        self.loader.load()

        self.assertFalse(self.loader.load_attempted)
        self.assertTrue(self.loader.loaded)
        self.loader.instance.default_shutdown.assert_not_called()
        self.load_skill_mock.assert_not_called()
        self.assertListEqual([], self.message_bus_mock.message_types)

    def test_skill_reload(self):
        self._build_skill_instance_mock()
        self.load_skill_mock.return_value = self.loader.instance
        self.loader.active = True
        self.loader.loaded = True
        self.loader.last_modified = 0
        self.loader.id = 'test_skill'
        with patch(self.mock_package + 'create_skill_descriptor') as csd_mock:
            self.loader.load()
            csd_mock.assert_called_once_with(str(self.skill_directory))
            self.load_skill_mock.assert_called_once_with(
                csd_mock.return_value,
                self.message_bus_mock,
                'test_skill',
                []
            )

        self.assertTrue(self.loader.load_attempted)
        self.assertTrue(self.loader.loaded)
        self.assertLess(0, self.loader.last_loaded)
        self.loader.instance.default_shutdown.assert_called_once()
        self.assertIn(
            'mycroft.skills.shutdown',
            self.message_bus_mock.message_types
        )
        self.assertIn(
            'mycroft.skills.loaded',
            self.message_bus_mock.message_types
        )

    def test_skill_load(self):
        self._build_skill_instance_mock()
        self.load_skill_mock.return_value = self.loader.instance
        self.loader.active = True
        self.loader.loaded = False
        self.loader.id = 'test_skill'
        with patch(self.mock_package + 'create_skill_descriptor') as csd_mock:
            self.loader.load()
            csd_mock.assert_called_once_with(str(self.skill_directory))
            self.load_skill_mock.assert_called_once_with(
                csd_mock.return_value,
                self.message_bus_mock,
                'test_skill',
                []
            )

        self.assertTrue(self.loader.load_attempted)
        self.assertTrue(self.loader.loaded)
        self.assertLess(0, self.loader.last_loaded)
        self.loader.instance.default_shutdown.assert_not_called()
        self.assertListEqual(
            ['mycroft.skills.loaded'],
            self.message_bus_mock.message_types
        )

    def test_skill_load_failure(self):
        self._build_skill_instance_mock()
        self.load_skill_mock.return_value = None
        with patch(self.mock_package + 'create_skill_descriptor') as csd_mock:
            self.loader.load()
            csd_mock.assert_called_once_with(str(self.skill_directory))
            self.load_skill_mock.assert_called_once_with(
                csd_mock.return_value,
                self.message_bus_mock,
                'test_skill',
                []
            )

        self.assertTrue(self.loader.load_attempted)
        self.assertFalse(self.loader.loaded)
        self.assertEqual(0, self.loader.last_loaded)
        self.assertListEqual(
            ['mycroft.skills.loading_failure'],
            self.message_bus_mock.message_types
        )

    def _build_skill_instance_mock(self):
        self.loader.instance = Mock()
        self.loader.instance.name = 'TestSkill'
        self.loader.instance.reload_skill = True
        self.loader.instance.default_shutdown = Mock()
