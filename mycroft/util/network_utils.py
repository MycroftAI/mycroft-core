import asyncio
import requests
import socket
import threading
import typing
from enum import Enum
from urllib.request import urlopen
from urllib.error import URLError

from dbus_next import BusType
from dbus_next.aio import MessageBus
from dbus_next.message import Message, MessageType

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


# -----------------------------------------------------------------------------


class ConnectivityState(int, Enum):
    """ State of network/internet connectivity.

    See also:
    https://developer-old.gnome.org/NetworkManager/stable/nm-dbus-types.html
    """

    UNKNOWN = 0
    """Network connectivity is unknown."""

    NONE = 1
    """The host is not connected to any network."""

    PORTAL = 2
    """The Internet connection is hijacked by a captive portal gateway."""

    LIMITED = 3
    """The host is connected to a network, does not appear to be able to reach
    the full Internet, but a captive portal has not been detected."""

    FULL = 4
    """The host is connected to a network, and appears to be able to reach the
    full Internet."""


class NetworkManager:
    """Connects to org.freedesktop.NetworkManager over DBus to
    determine connectivity."""

    DEFAULT_TIMEOUT = 1.0

    def __init__(self, dbus_address: typing.Optional[str] = None):
        self.dbus_address = dbus_address
        self.state: ConnectivityState = ConnectivityState.UNKNOWN

        # Events used to communicate with DBus thread
        self._state_requested = threading.Event()
        self._state_ready = threading.Event()

        # Run DBus message in a separate thread with its own asyncio loop
        self._dbus_thread = threading.Thread(
            target=self._dbus_thread_proc,
            daemon=True,
        )

        self._dbus_thread.start()

    def get_state(self, timeout=DEFAULT_TIMEOUT) -> ConnectivityState:
        """Gets the current connectivity state."""
        self._state_ready.clear()
        self._state_requested.set()
        self._state_ready.wait(timeout=timeout)
        return self.state

    def is_network_connected(self, timeout=DEFAULT_TIMEOUT) -> bool:
        """True if the network is connected, but internet may not be
        reachable."""
        return self.get_state(timeout=timeout) in {
            ConnectivityState.PORTAL,
            ConnectivityState.LIMITED,
            ConnectivityState.FULL,
        }

    def is_internet_connected(self, timeout=DEFAULT_TIMEOUT) -> bool:
        """True if the internet is reachable."""
        return self.get_state(timeout=timeout) == ConnectivityState.FULL

    def _dbus_thread_proc(self):
        """Run separate asyncio loop for DBus"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._dbus_thread_proc_async())
        loop.close()

    async def _dbus_thread_proc_async(self):
        """Connects to DBus and waits for requests from main thread."""
        try:
            if self.dbus_address:
                # Use custom session bus
                bus = MessageBus(bus_address=self.dbus_address)
            else:
                # Use system bus
                bus = MessageBus(bus_type=BusType.SYSTEM)

            await bus.connect()

            while True:
                # State update requested from main thread
                self._state_requested.wait()
                self.state = ConnectivityState.UNKNOWN

                reply = await bus.call(
                    Message(
                        destination="org.freedesktop.NetworkManager",
                        path="/org/freedesktop/NetworkManager",
                        interface="org.freedesktop.NetworkManager",
                        member="CheckConnectivity"
                    ))

                if reply.message_type != MessageType.ERROR:
                    self.state = ConnectivityState(reply.body[0])

                # Signal main thread that state is ready
                self._state_requested.clear()
                self._state_ready.set()
        except Exception:
            LOG.exception("network-manager")
