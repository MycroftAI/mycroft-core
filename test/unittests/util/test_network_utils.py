from unittest import TestCase, mock

from mycroft.util.network_utils import connected


class TestNetworkConnected(TestCase):
    def test_default_config_succeeds(self):
        """Check that happy path succeeds"""
        self.assertTrue(connected())


@mock.patch("mycroft.configuration.Configuration")
class TestNetworkFailure(TestCase):
    def test_dns_and_ncsi_fail(self, mock_conf):
        """Check that DNS and NCSI failure results in False response"""
        mock_conf.get.return_value = {
            "network_tests": {
                "dns_primary": "127.0.0.1",
                "dns_secondary": "127.0.0.1",
                "web_url": "https://www.google.com",
                "ncsi_endpoint": "http://www.msftncsi.com/ncsi.txt",
                "ncsi_expected_text": "Unexpected text",
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
                "ncsi_expected_text": "Microsoft NCSI",
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
                "ncsi_expected_text": "Microsoft NCSI",
            }
        }
        self.assertFalse(connected())
