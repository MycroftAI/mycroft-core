#!/usr/bin/env python3
import argparse
import logging
import os
import socket
import subprocess
import typing

# -----------------------------------------------------------------------------

SSID = "Mycroft"
USER_ID = 1050
GROUP_ID = USER_ID

EVENT_CREATE = "create-hotspot"
EVENT_CREATED = "hotspot-created"
EVENT_CONNECTED = "user-connected"
EVENT_DESTROYED = "hotspot-destroyed"

_LOGGER = logging.getLogger("wifi-connect")

# -----------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True, help="Path to Unix domain socket")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

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

    hotspot_proc: typing.Optional[subprocess.Popen] = None

    while True:
        try:
            connection, _client_address = sock.accept()
            with connection, connection.makefile(mode="rw") as conn_file:
                print("hello", file=conn_file, flush=True)

                for line in conn_file:
                    line = line.strip()

                    # Wait for event from Mycroft
                    if line == EVENT_CREATE:
                        _LOGGER.info("Creating hotspot: %s", SSID)

                        _cleanup_hotspot()
                        if hotspot_proc is not None:
                            hotspot_proc.terminate()
                            hotspot_proc = None

                        hotspot_proc = _create_hotspot()

                        # Watch output from wifi-connect
                        for hs_line in hotspot_proc.stdout:
                            hs_line = hs_line.strip().lower()
                            if "created" in hs_line:
                                # Hotspot is ready
                                _LOGGER.info("Hotspot created")
                                print(EVENT_CREATED, file=conn_file, flush=True)
                            elif "user connected" in hs_line:
                                # User is viewing the portal page
                                _LOGGER.info("User connected")
                                print(EVENT_CONNECTED, file=conn_file, flush=True)

                        # Block until wifi-connect exists
                        hotspot_proc.communicate()
                        _cleanup_hotspot()

                        _LOGGER.info("Hotspot destroyed")
                        print(EVENT_DESTROYED, file=conn_file, flush=True)
                        hotspot_proc = None
        except KeyboardInterrupt:
            break
        except Exception:
            _LOGGER.exception("Error communicating with socket client")
        finally:
            _cleanup_hotspot()


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
