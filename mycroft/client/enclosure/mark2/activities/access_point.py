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
"""Activity that communicates with awconnect.

Talks to a Python server running in the awconnect container to manage the
Mycroft access point. Receives messages over a file-based socket indicating when
the user interacts with the access point and its captive portal page.
"""
import socket

from mycroft.activity import Activity
from mycroft.messagebus import Message
from mycroft.util import LOG

SOCKET_PATH = "/awconnect/tmp/mycroft_socket"

EVENT_CREATE = "create-ap"
EVENT_CREATED = "ap-created"
EVENT_VISITED_PORTAL = "user-visited-portal"
EVENT_ENTERED_CREDS = "user-entered-credentials"
EVENT_DESTROYED = "ap-destroyed"


class AccessPointActivity(Activity):
    """Communicates with awconnect server to manage Mycroft access point.

    Messages are sent and received as lines of text over the socket.
    """

    def _run(self):
        # Connect to file-based socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)

        with sock.makefile(mode="rw") as conn_file:
            # Wait for hello
            LOG.debug("Waiting for hello message")
            conn_file.readline()
            LOG.info("Connected to awconnect")

            # Request that access point is created
            print(EVENT_CREATE, file=conn_file, flush=True)

            for line in conn_file:
                line = line.strip()

                if line == EVENT_CREATED:
                    LOG.info("Access point created")
                    self.bus.emit(
                        Message("hardware.awconnect.ap-activated")
                    )
                elif line == EVENT_VISITED_PORTAL:
                    LOG.info("User viewed captive portal page")
                    self.bus.emit(
                        Message("hardware.awconnect.portal-viewed")
                    )
                elif line == EVENT_ENTERED_CREDS:
                    LOG.info("User entered wifi credentials")
                    self.bus.emit(
                        Message("hardware.awconnect.credentials-entered")
                    )
                elif line == EVENT_DESTROYED:
                    LOG.info("Access point destroyed")
                    self.bus.emit(
                        Message("hardware.awconnect.ap-deactivated")
                    )
