import tempfile
from pathlib import Path
from shutil import rmtree
from unittest import TestCase
from unittest.mock import patch

from .mocks import mock_msm, mock_config, MessageBusMock


class MycroftUnitTestBase(TestCase):
    mock_package = None
    use_msm_mock = False

    def setUp(self):
        temp_dir = tempfile.mkdtemp()
        self.temp_dir = Path(temp_dir)
        self.message_bus_mock = MessageBusMock()
        self._mock_msm()
        self._mock_config()
        self._mock_log()

    def _mock_msm(self):
        if self.use_msm_mock:
            msm_patch = patch(self.mock_package + 'create_msm')
            self.addCleanup(msm_patch.stop)
            self.create_msm_mock = msm_patch.start()
            self.msm_mock = mock_msm(self.temp_dir)
            self.create_msm_mock.return_value = self.msm_mock

    def _mock_config(self):
        config_mgr_patch = patch(self.mock_package + 'Configuration')
        self.addCleanup(config_mgr_patch.stop)
        self.config_mgr_mock = config_mgr_patch.start()
        self.config_mgr_mock.get = mock_config(self.temp_dir)

    def _mock_log(self):
        log_patch = patch(self.mock_package + 'LOG')
        self.addCleanup(log_patch.stop)
        self.log_mock = log_patch.start()

    def tearDown(self):
        rmtree(str(self.temp_dir))
