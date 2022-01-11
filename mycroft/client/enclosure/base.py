# Copyright 2017 Mycroft AI Inc.
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
from threading import Lock

from mycroft import dialog
from mycroft.api import BackendDown, DeviceApi, is_paired
from mycroft.configuration import Configuration
from mycroft.messagebus.client import MessageBusClient
from mycroft.util import start_message_bus_client
from mycroft.util.log import LOG

from mycroft.messagebus.message import Message


write_lock = Lock()


class Enclosure:
    is_raspberry_pi_platform = False

    def __init__(self):
        # Load full config
        config = Configuration.get()
        self.lang = config['lang']
        self.config = config.get("enclosure")
        self.global_config = config

        # Create Message Bus Client
        self.bus = MessageBusClient()
        self.is_authenticated = False
        self.server_unavailable = False
        self.bus.on('mycroft.internet.connected',
                    self.handle_internet_connected)

    def run(self):
        """Start the Enclosure after it has been constructed."""
        # Allow exceptions to be raised to the Enclosure Service
        # if they may cause the Service to fail.
        start_message_bus_client("ENCLOSURE", self.bus)

    def stop(self):
        """Perform any enclosure shutdown processes."""
        pass

    def handle_internet_connected(self, _):
        self._update_system_clock()
        self._authenticate_with_server()
        if not self.is_authenticated:
            self._update_system()
            if self.server_unavailable:
                self._notify_server_unavailable()
            else:
                self._pair_with_server()
        LOG.info("Device is ready for use, activating microphone")
        self.bus.emit(Message("mycroft.mic.unmute"))

    def _update_system_clock(self):
        """Force a sync of the local clock with the Network Time Protocol.

        The NTP sync is only forced on Raspberry Pi based devices.  The
        assumption being that these devices are only running Mycroft services.
        We don't want to sync the time on a Linux desktop device, for example,
        because it could have a negative impact on other software running on
        that device.
        """
        if self.is_raspberry_pi_platform:
            LOG.info('Updating the system clock via NTP...')
            response = self.bus.wait_for_response(Message('system.ntp.sync'),
                                                  'system.ntp.sync.complete',
                                                  15)
            if response is None:
                LOG.warning('System clock synchronization timed out.')
            else:
                LOG.info('System clock updated')

    def _authenticate_with_server(self):
        """Set an instance attribute indicating the device's pairing status"""
        try:
            self.is_authenticated = is_paired(ignore_errors=False)
        except BackendDown:
            LOG.error('Unable to reach server for authentication.')
            self.server_unavailable = True

        if self.is_authenticated:
            LOG.info('Device is paired')

    def _update_system(self):
        """Emit an update event that will be handled by the admin service."""
        LOG.info('Attempting system update...')
        msg_data = dict(paired=self.is_authenticated,
                        platform=self.config["platform"])
        msg = Message('system.update', msg_data)
        resp = self.bus.wait_for_response(msg, 'system.update.processing')

        if resp is not None and resp.data.get('processing', True):
            self.bus.wait_for_response(Message('system.update.waiting'),
                                       'system.update.complete',
                                       1000)

    def _pair_with_server(self):
        """Determine if device is paired, if not automatically start pairing.

        Pairing cannot be performed if there is no connection to the back end.
        So skip pairing if the backend is down.
        """
        LOG.info('Device not paired with server, beginning pairing process')
        payload = dict(utterances=["pair my device"], lang="en-us")
        self.bus.emit(Message("recognizer_loop:utterance", payload))

    def _update_device_on_server(self):
        """Communicate version information to the backend.

        The backend tracks core version, enclosure version, platform build
        and platform name for each device, if it is known.
        """
        if self.is_authenticated:
            LOG.info('Sending latest device attributes to the server...')
            try:
                api = DeviceApi()
                api.update_version()
            except Exception:
                LOG.error("Failed to update device attributes on server")
            else:
                LOG.info("Server update of device attributes successful")

    def _notify_server_unavailable(self):
        """Notify user of inability to communicate with the backend."""
        self.bus.emit(Message("backend.down"))
        message_data = {'utterance': dialog.get("backend.down")}
        self.bus.emit(Message("speak", message_data))
