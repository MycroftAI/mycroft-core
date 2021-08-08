import requests
import socket
from urllib.request import urlopen
from urllib.error import URLError

from .log import LOG


# mycroft-core-zh: todo if conf is for zh, use baidu instead of google to check connected.
def connected():
    """Check connection by connecting to 8.8.8.8 and if google.com is
    reachable if this fails, Check Microsoft NCSI is used as a backup.

    Returns:
        True if internet connection can be detected
    """
    if True:
        return connected_baidu()
    else:
        if _connected_dns():
            # Outside IP is reachable check if names are resolvable
            return _connected_google()
        else:
            # DNS can't be reached, do a complete fetch in case it's blocked
            return _connected_ncsi()


def connected_baidu():
    """Check internet connection by retrieving the baidu endpoint.

    Returns:
        True if internet connection can be detected
    """
    try:
        r = requests.get('https://www.baidu.com')
        LOG.info(str(r))
        if r.status_code >= 200 and r.status_code < 300:
            return True
    except Exception:
        LOG.error('internet connection fails, unable to retrieve the baidu.')
    return False


def _connected_ncsi():
    """Check internet connection by retrieving the Microsoft NCSI endpoint.

    Returns:
        True if internet connection can be detected
    """
    try:
        r = requests.get('http://www.msftncsi.com/ncsi.txt')
        if r.text == 'Microsoft NCSI':
            return True
    except Exception:
        pass
    return False


def _connected_dns(host="8.8.8.8", port=53, timeout=3):
    """Check internet connection by connecting to DNS servers

    Returns:
        True if internet connection can be detected
    """
    # Thanks to 7h3rAm on
    # Host: 8.8.8.8 (google-public-dns-a.google.com)
    # OpenPort: 53/tcp
    # Service: domain (DNS/TCP)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        return True
    except IOError:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect(("8.8.4.4", port))
            return True
        except IOError:
            return False


def _connected_google():
    """Check internet connection by connecting to www.google.com
    Returns:
        True if connection attempt succeeded
    """
    connect_success = False
    try:
        urlopen('https://www.google.com', timeout=3)
    except URLError as ue:
        LOG.debug('Attempt to connect to internet failed: ' + str(ue.reason))
    else:
        connect_success = True

    return connect_success
