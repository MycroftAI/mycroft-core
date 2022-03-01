from unittest import TestCase, mock
from unittest.mock import patch
from mycroft.gui.extensions import SmartSpeakerExtension
from ..mocks import MessageBusMock
from mycroft.configuration import Configuration
from test.util import base_config
from mycroft.messagebus import Message

PATCH_MODULE = "mycroft.gui.extensions"

# Add Unit Tests For SmartSpeakerExtension

class TestSmartSpeakerExtension:
    @patch.object(Configuration, 'get')
    def test_smartspeaker_set_backend_type(self, mock_get):
        config = base_config()
        config.merge(
            {
                'gui': {
                    'extension': 'smartspeaker'
                }
            })
        mock_get.return_value = config
        smartSpeaker = SmartSpeakerExtension(MessageBusMock(), MessageBusMock())
        smartSpeaker.set_backend_type = mock.Mock()
        message_data = Message("ovos.pairing.set.backend", {'backend': 'unknown'})
        smartSpeaker.set_backend_type(message_data)
        smartSpeaker.set_backend_type.assert_any_call(message_data)

    @patch.object(Configuration, 'get')
    def test_smartspeaker_start_homescreen_process(self, mock_get):
        config = base_config()
        config.merge(
            {
                'gui': {
                    'extension': 'smartspeaker'
                }
            })
        mock_get.return_value = config
        smartSpeaker = SmartSpeakerExtension(MessageBusMock(), MessageBusMock())
        smartSpeaker.start_homescreen_process = mock.Mock()
        message_data = Message("ovos.pairing.process.completed", {})
        smartSpeaker.start_homescreen_process(message_data)
        smartSpeaker.start_homescreen_process.assert_any_call(message_data)
