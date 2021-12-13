#!/usr/bin/env python3
"""Small socket server for Mark II hotspot management.

Install into the awconnect container at /opt/wifi-connect/start
Will be automatically run by /etc/systemd/system/wifi-connect.service

Creates a Unix domain socket in /tmp to communicate with the WiFi connect skill.
"""
import argparse
import logging
import os
import socket
import subprocess
import threading
import typing

# -----------------------------------------------------------------------------

DEFAULT_SOCKET = "/tmp/mycroft_socket"

SSID = "Mycroft"
USER_ID = 1050
GROUP_ID = USER_ID

EVENT_CREATE = "create-hotspot"
EVENT_CREATED = "hotspot-created"
EVENT_CONNECTED = "user-connected"
EVENT_SELECTED = "user-selected"
EVENT_DESTROYED = "hotspot-destroyed"

_LOGGER = logging.getLogger("wifi-connect")

# -----------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--socket",
        default=DEFAULT_SOCKET,
        help="Path to Unix domain socket (default: {DEFAULT_SOCKET})",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    # Need to unlink socket if it exists
    try:
        os.unlink(args.socket)
    except OSError:
        pass

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(args.socket)
    sock.listen()

    # Give mycroft user access
    os.chown(args.socket, USER_ID, GROUP_ID)

    _LOGGER.info("Listening for clients on %s", args.socket)

    while True:
        try:
            connection, client_address = sock.accept()
            _LOGGER.debug("Connection from %s", client_address)

            # Start new thread for client
            threading.Thread(
                target=_client_thread, args=(connection,), daemon=True
            ).start()
        except KeyboardInterrupt:
            break
        except Exception:
            _LOGGER.exception("Error communicating with socket client")
        finally:
            _cleanup_hotspot()


# -----------------------------------------------------------------------------


def _client_thread(connection):
    hotspot_proc: typing.Optional[subprocess.Popen] = None

    try:
        with connection, connection.makefile(mode="rw") as conn_file:
            print("hello", file=conn_file, flush=True)

            for line in conn_file:
                line = line.strip()
                _LOGGER.debug("From client: %s", line)

                # Wait for event from Mycroft
                if line == EVENT_CREATE:
                    _LOGGER.info("Creating hotspot: %s", SSID)

                    _cleanup_hotspot()
                    if hotspot_proc is not None:
                        try:
                            hotspot_proc.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            hotspot_proc.kill()

                        hotspot_proc = None

                    hotspot_proc = _create_hotspot()

                    # Watch output from wifi-connect
                    for hs_line in hotspot_proc.stdout:
                        hs_line = hs_line.strip().lower()
                        _LOGGER.debug("wifi-connect: %s", hs_line)

                        if "created" in hs_line:
                            # Hotspot is ready
                            _LOGGER.info("Hotspot created")
                            print(EVENT_CREATED, file=conn_file, flush=True)
                        elif "user connected" in hs_line:
                            # User is viewing the portal page
                            _LOGGER.info("User connected")
                            print(EVENT_CONNECTED, file=conn_file, flush=True)
                        elif "received connection request" in hs_line:
                            # User has selected access point
                            _LOGGER.info("User selected access point")
                            print(EVENT_SELECTED, file=conn_file, flush=True)

                    # Block until wifi-connect exits
                    try:
                        hotspot_proc.communicate(timeout=1)
                    except subprocess.TimeoutExpired:
                        hotspot_proc.kill()

                    _cleanup_hotspot()

                    _LOGGER.info("Hotspot destroyed")
                    print(EVENT_DESTROYED, file=conn_file, flush=True)
                    hotspot_proc = None
    except Exception:
        _LOGGER.exception("Error in client thread")


# -----------------------------------------------------------------------------


def _cleanup_hotspot():
    """Delete existing hotspot if it exists"""
    subprocess.run(["nmcli", "connection", "delete", SSID], check=False)


def _create_hotspot() -> subprocess.Popen:
    """Create a new hotspot with wifi-connect"""
    return subprocess.Popen(
        [
            "/opt/wifi-connect/wifi-connect",
            "-u",
            "/opt/wifi-connect/ui/build",
            "-s",
            SSID,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
