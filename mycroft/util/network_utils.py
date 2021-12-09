import requests
import socket
from urllib.request import urlopen
from urllib.error import URLError

from .log import LOG


def _get_network_tests_config():
    """Get network_tests object from mycroft.configuration."""
    # Wrapped to avoid circular import errors.
    from mycroft.configuration import Configuration
    config = Configuration.get()
    return config.get('network_tests', {})


def connected():
    """Check connection by connecting to 8.8.8.8 and if google.com is
    reachable if this fails, Check Microsoft NCSI is used as a backup.

    Returns:
        True if internet connection can be detected
    """
    if _connected_dns():
        # Outside IP is reachable check if names are resolvable
        return _connected_google()
    else:
        # DNS can't be reached, do a complete fetch in case it's blocked
        return _connected_ncsi()


def _connected_ncsi():
    """Check internet connection by retrieving the Microsoft NCSI endpoint.

    Returns:
        True if internet connection can be detected
    """
    config = _get_network_tests_config()
    ncsi_endpoint = config.get('ncsi_endpoint')
    expected_text = config.get('ncsi_expected_text')
    try:
        r = requests.get(ncsi_endpoint)
        if r.text == expected_text:
            return True
    except Exception:
        LOG.error("Unable to verify connection via NCSI endpoint.")
    return False


def _connected_dns(host=None, port=53, timeout=3):
    """Check internet connection by connecting to DNS servers

    Returns:
        True if internet connection can be detected
    """
    # Thanks to 7h3rAm on
    # Host: 8.8.8.8 (google-public-dns-a.google.com)
    # OpenPort: 53/tcp
    # Service: domain (DNS/TCP)
    config = _get_network_tests_config()
    if host is None:
        host = config.get('dns_primary')
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        return True
    except IOError:
        LOG.error("Unable to connect to primary DNS server, "
                  "trying secondary...")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            dns_secondary = config.get('dns_secondary')
            s.connect((dns_secondary, port))
            return True
        except IOError:
            LOG.error("Unable to connect to secondary DNS server.")
            return False


def _connected_google():
    """Check internet connection by connecting to www.google.com
    Returns:
        True if connection attempt succeeded
    """
    connect_success = False
    config = _get_network_tests_config()
    url = config.get('web_url')
    try:
        urlopen(url, timeout=3)
    except URLError as ue:
        LOG.error('Attempt to connect to internet failed: ' + str(ue.reason))
    else:
        connect_success = True

    return connect_success
