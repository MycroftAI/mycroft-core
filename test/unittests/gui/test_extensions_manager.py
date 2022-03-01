from unittest import TestCase, mock
from unittest.mock import patch
from mycroft.gui.extensions import ExtensionsManager
from ..mocks import MessageBusMock
from mycroft.configuration import Configuration
from test.util import base_config

PATCH_MODULE = "mycroft.gui.extensions"

# Add Unit Tests For ExtensionManager

class TestExtensionManager:
    @patch.object(Configuration, 'get')
    def test_extension_manager_activate(self, mock_get):
        config = base_config()
        config.merge(
            {
                'gui': {
                    'extension': 'generic',
                    'generic': {
                        'homescreen_supported': False
                    }
                }
            })
        mock_get.return_value = config
        extension_manager = ExtensionsManager("ExtensionManager", MessageBusMock(), MessageBusMock())
        extension_manager.activate_extension = mock.Mock()
        extension_manager.activate_extension("generic")
        extension_manager.activate_extension.assert_any_call("generic")
