# Copyright 2021 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Utilities for network and internet detection."""
import socket
import subprocess
import typing
from urllib.request import urlopen
from urllib.error import URLError

import requests
from bs4 import BeautifulSoup

from dbus_next import BusType as DBusType
from dbus_next.aio import MessageBus as DBusMessageBus


from .log import LOG


def _get_network_tests_config():
    """Get network_tests object from mycroft.configuration."""
    # Wrapped to avoid circular import errors.
    from mycroft.configuration import Configuration

    config = Configuration.get()
    return config.get("network_tests", {})


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
    ncsi_endpoint = config.get("ncsi_endpoint")
    expected_text = config.get("ncsi_expected_text")
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
        host = config.get("dns_primary")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        return True
    except IOError:
        LOG.error("Unable to connect to primary DNS server, " "trying secondary...")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            dns_secondary = config.get("dns_secondary")
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
    url = config.get("web_url")
    try:
        urlopen(url, timeout=3)
    except URLError as ue:
        LOG.error("Attempt to connect to internet failed: " + str(ue.reason))
    else:
        connect_success = True

    return connect_success


def check_system_clock_sync_status() -> bool:
    """Return True if the system clock has been synchronized with NTP"""
    clock_synchronized = False

    try:
        timedatectl_result = subprocess.check_output(
            ["timedatectl", "show"], stderr=subprocess.STDOUT
        )
        timedatectl_stdout = timedatectl_result.decode().splitlines()

        for line in timedatectl_stdout:
            if line.strip() == "NTPSynchronized=yes":
                clock_synchronized = True
                break
    except subprocess.CalledProcessError as error:
        LOG.exception("error while checking system clock sync: %s", error.output)

    return clock_synchronized


def check_captive_portal() -> bool:
    """Returns True if a captive portal page is detected"""
    captive_portal = False

    try:
        # We need to check a site that doesn't use HTTPS
        html_doc = requests.get("http://start.mycroft.ai/portal-check.html").text
        soup = BeautifulSoup(html_doc)
        title = soup.title.string if soup.title else ""

        LOG.info(title)

        # If something different is in the title, we likely were redirected
        # to the portal page.
        if title.lower().strip() != "portal check":
            captive_portal = True
    except Exception:
        LOG.exception("Error checking for captive portal")

    return captive_portal


# -----------------------------------------------------------------------------


NM_NAMESPACE = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"


def get_dbus(bus_address: typing.Optional[str] = None) -> DBusMessageBus:
    """Get DBus message bus"""

    if bus_address:
        # Configured bus
        return DBusMessageBus(bus_address=bus_address)

    # System bus
    return DBusMessageBus(bus_type=DBusType.SYSTEM)


async def get_network_manager(dbus: DBusMessageBus):
    """Get DBus object, interface to NetworkManager"""
    introspection = await dbus.introspect(NM_NAMESPACE, NM_PATH)

    nm_object = dbus.get_proxy_object(NM_NAMESPACE, NM_PATH, introspection)

    return nm_object, nm_object.get_interface(NM_NAMESPACE)
