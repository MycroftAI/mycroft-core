#!/usr/bin/env python3
import socket

from mycroft.activity import ThreadActivity
from mycroft.messagebus import Message

SOCKET_PATH = "/awconnect/tmp/mycroft_socket"

EVENT_CREATE = "create-hotspot"
EVENT_CREATED = "hotspot-created"
EVENT_CONNECTED = "user-connected"
EVENT_DESTROYED = "hotspot-destroyed"


class HotspotActivity(ThreadActivity):
    """Communicates with awconnect to manage hotspot"""

    def started(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)

        with sock.makefile(mode="rw") as conn_file:
            # Wait for hello
            conn_file.readline()

            # Request that hotspot is created
            print(EVENT_CREATE, file=conn_file, flush=True)

            for line in conn_file:
                line = line.strip()

                if line == EVENT_CREATED:
                    self.log.info("Hotspot created")
                    self.bus.emit(
                        Message("system.wifi.setup.hotspot-activated")
                    )
                elif line == EVENT_CONNECTED:
                    self.log.info("User connected to hotspot")
                    self.bus.emit(
                        Message("system.wifi.setup.hotspot-connected")
                    )
                elif line == EVENT_DESTROYED:
                    self.log.info("Wi-Fi setup complete")
                    self.bus.emit(Message("system.wifi.setup.connected"))
