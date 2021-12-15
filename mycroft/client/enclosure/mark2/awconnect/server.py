#!/usr/bin/env python3
#
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
"""Small socket server for Mark II access point management.

Install into the awconnect container at /opt/wifi-connect/start
Will be automatically run by /etc/systemd/system/wifi-connect.service

Creates a Unix domain socket at /tmp/mycroft_socket to communicate with the WiFi
connect skill.

An alternative approach would have been to use DBus, but permission issues from
the mycroft container side prevented this. In the interest of time, this
approach was taken.
"""
import argparse
import logging
import os
import socket
import subprocess
import threading
import typing


DEFAULT_SOCKET = "/tmp/mycroft_socket"

SSID = "Mycroft"
USER_ID = 1050  # hard-coded in awconnect
GROUP_ID = USER_ID

EVENT_CREATE = "create-ap"
EVENT_CREATED = "ap-created"
EVENT_VISITED_PORTAL = "user-visited-portal"
EVENT_ENTERED_CREDS = "user-entered-credentials"
EVENT_DESTROYED = "ap-destroyed"

_LOGGER = logging.getLogger("wifi-connect")

_ACCESS_POINT_PROC: typing.Optional[subprocess.Popen] = None


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
            _cleanup_access_point()


# -----------------------------------------------------------------------------


def _client_thread(connection):
    # The global variable is poor form, but we can't have two wifi-connect
    # processes running at the same time.
    #
    # Additionally, we can't run this code on the main thread because
    # socket.accept() will miss clients.
    global _ACCESS_POINT_PROC

    try:
        with connection, connection.makefile(mode="rw") as conn_file:
            print("hello", file=conn_file, flush=True)

            for line in conn_file:
                line = line.strip()
                _LOGGER.debug("From client: %s", line)

                # Wait for event from Mycroft
                if line == EVENT_CREATE:
                    _LOGGER.info("Creating access point: %s", SSID)

                    _cleanup_access_point()
                    if _ACCESS_POINT_PROC is not None:
                        try:
                            _ACCESS_POINT_PROC.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            _ACCESS_POINT_PROC.kill()

                        _ACCESS_POINT_PROC = None

                    _ACCESS_POINT_PROC = _create_access_point()

                    # Watch output from wifi-connect
                    for hs_line in _ACCESS_POINT_PROC.stdout:
                        hs_line = hs_line.strip().lower()
                        _LOGGER.debug("wifi-connect: %s", hs_line)

                        if "created" in hs_line:
                            _LOGGER.info("Access point created")
                            print(EVENT_CREATED, file=conn_file, flush=True)
                        elif "user connected" in hs_line:
                            _LOGGER.info("User visited portal page")
                            print(
                                EVENT_VISITED_PORTAL,
                                file=conn_file,
                                flush=True,
                            )
                        elif "received connection request" in hs_line:
                            _LOGGER.info("User has entered credentials")
                            print(
                                EVENT_ENTERED_CREDS, file=conn_file, flush=True
                            )
                        elif "stopping" in hs_line:
                            _LOGGER.info("Access point destroyed")
                            print(EVENT_DESTROYED, file=conn_file, flush=True)

                    # Block until wifi-connect exits
                    if _ACCESS_POINT_PROC is not None:
                        try:
                            _ACCESS_POINT_PROC.communicate(timeout=1)
                        except subprocess.TimeoutExpired:
                            _ACCESS_POINT_PROC.kill()

                        _cleanup_access_point()

                    _ACCESS_POINT_PROC = None
    except Exception:
        _LOGGER.exception("Error in client thread")


# -----------------------------------------------------------------------------


def _cleanup_access_point():
    """Delete existing access point if it exists"""
    subprocess.run(["nmcli", "connection", "delete", SSID], check=False)


def _create_access_point() -> subprocess.Popen:
    """Create a new access point with wifi-connect"""
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
