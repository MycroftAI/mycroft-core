import unittest
from unittest import TestCase, mock

from mycroft.util.network_utils import connected


class TestNetworkConnected(TestCase):
    def test_default_config_succeeds(self):
        """Check that happy path succeeds"""
        self.assertTrue(connected())


@mock.patch('mycroft.configuration.Configuration')
class TestNetworkFailure(TestCase):

    def test_dns_and_ncsi_fail(self, mock_conf):
        """Check that DNS and NCSI failure results in False response"""
        mock_conf.get.return_value = {
            "network_tests": {
                "dns_primary": "127.0.0.1",
                "dns_secondary": "127.0.0.1",
                "web_url": "https://www.google.com",
                "ncsi_endpoint": "http://www.msftncsi.com/ncsi.txt",
                "ncsi_expected_text": "Unexpected text"
            }
        }
        self.assertFalse(connected())

    def test_secondary_dns_succeeds(self, mock_conf):
        """Check that only primary DNS failing still succeeds"""
        mock_conf.get.return_value = {
            "network_tests": {
                "dns_primary": "127.0.0.1",
                "dns_secondary": "8.8.4.4",
                "web_url": "https://www.google.com",
                "ncsi_endpoint": "http://www.msftncsi.com/ncsi.txt",
                "ncsi_expected_text": "Microsoft NCSI"
            }
        }
        self.assertTrue(connected())

    def test_dns_success_url_fail(self, mock_conf):
        """Check that URL connection failure results in False response"""
        mock_conf.get.return_value = {
            "network_tests": {
                "dns_primary": "8.8.8.8",
                "dns_secondary": "8.8.4.4",
                "web_url": "https://test.invalid",
                "ncsi_endpoint": "http://www.msftncsi.com/ncsi.txt",
                "ncsi_expected_text": "Microsoft NCSI"
            }
        }
        self.assertFalse(connected())


@unittest.skip("Tests need to be fixed.")
@mock.patch('mycroft.util.network_utils.MessageBus', autospec=True)
class TestNetworkManager(TestCase):

    def test_full_connectivity(self, mock_bus):
        """Check network/internet connectivity"""
        reply = mock.MagicMock()
    # COMMENTED OUT TO SILENCE FLAKE8 - OBJECTS NO LONGER EXIST
    #     reply.message_type.return_value = MessageType.METHOD_RETURN
    #     reply.body.__getitem__.return_value = ConnectivityState.FULL.value
    #     mock_bus.call.return_value = reply

    #     net_manager = NetworkManager(bus=mock_bus)
    #     self.assertTrue(net_manager.is_network_connected())
    #     self.assertTrue(net_manager.is_internet_connected())

    #     mock_bus.call.assert_awaited()

    # def test_limited_connectivity(self, mock_bus):
    #     """Check network connectivity only"""
    #     reply = mock.MagicMock()
    #     reply.message_type.return_value = MessageType.METHOD_RETURN
    #     reply.body.__getitem__.return_value = ConnectivityState.LIMITED.value
    #     mock_bus.call.return_value = reply

    #     net_manager = NetworkManager(bus=mock_bus)
    #     self.assertTrue(net_manager.is_network_connected())
    #     self.assertFalse(net_manager.is_internet_connected())

    #     mock_bus.call.assert_awaited()

    # def test_bus_error(self, mock_bus):
    #     """Ensure DBus thread is restarted if an error occurs"""
    #     net_manager = NetworkManager(bus=mock_bus)
    #     mock_bus.call.side_effect = RuntimeError("fake DBus error")

    #     # Should report no connectivity
    #     self.assertFalse(net_manager.is_network_connected())

    #     # Bus has been restored
    #     mock_bus.call.side_effect = None

    #     reply = mock.MagicMock()
    #     reply.message_type.return_value = MessageType.METHOD_RETURN
    #     reply.body.__getitem__.return_value = ConnectivityState.FULL.value
    #     mock_bus.call.return_value = reply

    #     self.assertTrue(net_manager.is_network_connected())
    #     self.assertTrue(net_manager.is_internet_connected())
