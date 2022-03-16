# Copyright 2019 Mycroft AI Inc.
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
"""Checks network connectivity using DBus and NetworkManager"""
import asyncio
import typing
from enum import Enum

from mycroft.activity import Activity
from mycroft.messagebus import Message
from mycroft.util.log import LOG
from mycroft.util.network_utils import (
    get_dbus,
    get_network_manager,
    NM_NAMESPACE,
)

# Network manager state
# https://developer-old.gnome.org/NetworkManager/stable/nm-dbus-types.html#NMDeviceState

NM_DEVICE_STATE_DISCONNECTED = 30
NM_DEVICE_STATE_ACTIVATED = 100

# NetworkManager constants
NM_DEVICE_TYPE_ETHERNET = 1
NM_DEVICE_TYPE_WIFI = 2

NM_802_11_MODE_UNKNOWN = 0
NM_802_11_MODE_INFRA = 2

# Seconds to check device statuses before declaring that the network is not
# connected.
NOT_CONNECTED_TIMEOUT = 60.0


class DeviceState(str, Enum):
    """State of a network device"""

    NOT_CONNECTED = "not-connected"
    """Device is not connected to a network"""

    NOT_READY = "not-ready"
    """Connectivity cannot be determined yet"""

    CONNECTED = "connected"
    """Device is connected to a network"""


class NetworkDevice:
    """DBus network device"""

    DISCONNECT_RETRIES = 20
    DISCONNECT_WAIT = 1.0
    """Seconds to wait before re-checking disconnected state.

    Devices pass through a disconnected state when switching modes, so we don't
    want to report "not connected" too early.
    """

    def __init__(self, name: str, dev_interface, props_interface):
        self.name = name
        self.dev_interface = dev_interface
        self.props_interface = props_interface

    async def is_connected(self) -> DeviceState:
        """Return device connected state.

        A "not ready" device will be checked again when one if its properties
        has changed.
        """
        state = NM_DEVICE_STATE_DISCONNECTED
        for i in range(NetworkDevice.DISCONNECT_RETRIES):
            # Only check state
            state = await self.dev_interface.get_state()
            LOG.info("Attempt %s - %s state: %s", i + 1, self.name, state)

            if state == NM_DEVICE_STATE_ACTIVATED:
                return DeviceState.CONNECTED

            # Wait and check again
            await asyncio.sleep(NetworkDevice.DISCONNECT_WAIT)

        if state <= NM_DEVICE_STATE_DISCONNECTED:
            return DeviceState.NOT_CONNECTED

        return DeviceState.NOT_READY


class WiFiDevice(NetworkDevice):
    """DBus wireless network device"""

    def __init__(self, name: str, dev_interface, props_interface, wireless_interface):
        super().__init__(name, dev_interface, props_interface)
        self.wireless_interface = wireless_interface

    async def is_connected(self) -> DeviceState:
        mode = await self.wireless_interface.get_mode()
        LOG.debug("%s mode: %s", self.name, mode)

        if mode != NM_802_11_MODE_INFRA:
            return DeviceState.NOT_READY

        # Only check state if *not* in access point mode.
        # It will always report connected otherwise.
        return await super().is_connected()


class NoNetworkDevicesError(Exception):
    """Raised when no network devices are found on DBus"""

    pass


class NetworkConnectActivity(Activity):
    """Determines network connectivity using DBus NetworkManager"""

    def __init__(self, name: str, bus, dbus_address: typing.Optional[str] = None):
        super().__init__(name, bus)

        self._dbus_address = dbus_address
        self._props_changed: typing.Optional[asyncio.Event] = None
        self._error: typing.Optional[Exception] = None

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._activity_proc_async())
        loop.close()

        if self._error is not None:
            # Ensure ended success is set correctly
            raise self._error

    async def _activity_proc_async(self):
        self._props_changed = asyncio.Event()

        try:
            dbus = get_dbus(self._dbus_address)
            await dbus.connect()

            _nm_object, nm_interface = await get_network_manager(dbus)

            # Find wi-fi and ethernet devices
            devices = await self._get_network_devices(dbus, nm_interface)

            if not devices:
                # Will raise in _run
                self._error = NoNetworkDevicesError("No network devices found on DBus")
                return

            self._subscribe_to_signals(devices)

            # Check for connectivity with a timeout
            connected = False
            try:
                connected = await asyncio.wait_for(
                    self._is_connected(devices), NOT_CONNECTED_TIMEOUT
                )
            except asyncio.TimeoutError:
                # Not connected
                LOG.warning("Timeout occurred while checking for network connectivity")

            if connected:
                # Report connected
                LOG.info("Network connection detected")
                self.bus.emit(Message("hardware.network-detected"))
            else:
                # Report not connected
                self.bus.emit(Message("hardware.network-not-detected"))
                LOG.info("Network connection not detected")

            self._cleanup(devices)
            await dbus.wait_for_disconnect()
        except Exception as error:
            LOG.exception("error while checking for network connectivity")
            self._error = error  # will raise in _run

    def _subscribe_to_signals(self, devices):
        """Watch all network devices for property changes"""
        for device in devices:
            # Subscribe to state updates
            device.props_interface.on_properties_changed(self._dev_props_changed)

    def _dev_props_changed(self, _interface, _changed_props, _invalidated_props):
        """Callback for properties changed signal"""
        if self._props_changed is not None:
            self._props_changed.set()

    async def _wait_for_connectivity(self, devices):
        """Wait until at least one network device is connected"""
        await self._props_changed.wait()

        while not await self._is_connected(devices):
            self._props_changed.clear()
            await self._props_changed.wait()

    async def _is_connected(self, devices):
        """True if any device is connected"""
        while True:
            all_disconnected = True

            connected_aws = [device.is_connected() for device in devices]
            for connected_result in asyncio.as_completed(connected_aws):
                state = await connected_result
                if state == DeviceState.CONNECTED:
                    LOG.info("Device connected")
                    return True

                if state == DeviceState.NOT_READY:
                    all_disconnected = False

            if all_disconnected:
                break

            await self._props_changed.wait()

        return False

    def _cleanup(self, devices):
        """Remove signal handlers"""
        for device in devices:
            device.props_interface.off_properties_changed(self._dev_props_changed)

    async def _get_network_devices(
        self, dbus, nm_interface
    ) -> typing.List[NetworkDevice]:
        """Get DBus interfaces and is_connected methods for network devices"""
        network_devices: typing.List[NetworkDevice] = []

        for device_path in await nm_interface.get_all_devices():
            dev_introspect = await dbus.introspect(NM_NAMESPACE, device_path)
            dev_object = dbus.get_proxy_object(
                NM_NAMESPACE, device_path, dev_introspect
            )

            dev_interface = dev_object.get_interface(f"{NM_NAMESPACE}.Device",)

            dev_type = await dev_interface.get_device_type()

            # Only pay attention to ethernet and wifi devices
            if dev_type in {NM_DEVICE_TYPE_ETHERNET, NM_DEVICE_TYPE_WIFI}:
                LOG.debug("Network device found: %s", device_path)

                # Get access to PropertiesChanged signal
                dev_props_interface = dev_object.get_interface(
                    "org.freedesktop.DBus.Properties"
                )

                if dev_type == NM_DEVICE_TYPE_WIFI:
                    dev_name = await dev_interface.get_interface()

                    # Need to check for AP mode before looking at
                    # connectivity state.
                    #
                    # Otherwise, the Wi-Fi device reports itself as
                    # connected...to itself.
                    wireless_interface = dev_object.get_interface(
                        f"{NM_NAMESPACE}.Device.Wireless",
                    )

                    network_devices.append(
                        WiFiDevice(
                            dev_name,
                            dev_interface,
                            dev_props_interface,
                            wireless_interface,
                        )
                    )
                else:
                    dev_name = await dev_interface.get_interface()

                    # Just use device state for ethernet
                    network_devices.append(
                        NetworkDevice(dev_name, dev_interface, dev_props_interface)
                    )

        return network_devices
