#!/usr/bin/env python3
import asyncio
import threading
import typing

from mycroft.activity import Activity
from mycroft.messagebus import Message
from mycroft.util.network_utils import (
    get_dbus,
    get_network_manager,
    NM_NAMESPACE,
)

# Network manager state
# https://developer-old.gnome.org/NetworkManager/stable/nm-dbus-types.html#NMState

NOT_CONNECTED = 0
NETWORK_CONNECTED = 60

# NetworkManager constants
NM_DEVICE_TYPE_ETHERNET = 1
NM_DEVICE_TYPE_WIFI = 2

NM_802_11_MODE_UNKNOWN = 0
NM_802_11_MODE_INFRA = 2


class NetworkConnectActivity(Activity):
    """Determines network connectivity using DBus NetworkManager"""

    def __init__(
        self, name: str, bus, bus_address: typing.Optional[str] = None
    ):
        super().__init__(name, bus)

        self._bus_address = bus_address
        self._async_thread: typing.Optional[threading.Thread] = None
        self._props_changed: typing.Optional[asyncio.Event] = None

    def started(self):
        self._async_thread = threading.Thread(
            target=self._activity_proc, daemon=True
        )
        self._async_thread.start()

    def ended(self):
        if self._async_thread is not None:
            self._async_thread.join(timeout=1.0)
            self._async_thread = None

    def _activity_proc(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._activity_proc_async())
        loop.close()

        self.end()

    async def _activity_proc_async(self):
        self._props_changed = asyncio.Event()

        try:
            dbus = get_dbus()
            await dbus.connect()

            _nm_object, nm_interface = await get_network_manager(dbus)

            # Find wi-fi and ethernet devices
            network_props_interfaces = await self._get_network_devices(
                dbus, nm_interface
            )

            assert network_props_interfaces, "No network devices found on DBus"

            for dev_props_interface, _ in network_props_interfaces:
                # Subscribe to state updates
                dev_props_interface.on_properties_changed(
                    self._dev_props_changed
                )

            async def is_connected():
                """True if any device is connected"""
                for _, is_dev_connected in network_props_interfaces:
                    if await is_dev_connected():
                        return True

                return False

            # Initial connectivity check
            if not (await is_connected()):
                # Report not connected
                self.bus.emit(Message("hardware.network-not-detected"))
                self.log.info("Network connection not detected")

                # Wait until connected
                await self._props_changed.wait()

                while not (await is_connected()):
                    self._props_changed.clear()
                    await self._props_changed.wait()

            # Report connected
            self.bus.emit(Message("hardware.network-detected"))
            self.log.info("Network connection detected")

            # Clean up
            for dev_props_interface, _ in network_props_interfaces:
                dev_props_interface.off_properties_changed(
                    self._dev_props_changed
                )

            await dbus.wait_for_disconnect()
        except Exception as error:
            self.log.exception("error while checking for network connectivity")
            self.bus.emit(
                Message(f"{self.name}.error", data={"error": str(error)})
            )

    async def _get_network_devices(self, dbus, nm_interface):
        """Get DBus interfaces and is_connected methods for network devices"""
        # Pairs of (dbus_props_interface, is_device_connected)
        network_devices = []

        for device_path in await nm_interface.get_all_devices():
            dev_introspect = await dbus.introspect(NM_NAMESPACE, device_path)
            dev_object = dbus.get_proxy_object(
                NM_NAMESPACE, device_path, dev_introspect
            )

            dev_interface = dev_object.get_interface(f"{NM_NAMESPACE}.Device",)

            dev_type = await dev_interface.get_device_type()

            # TODO: Include ethernet
            # if dev_type in {NM_DEVICE_TYPE_ETHERNET, NM_DEVICE_TYPE_WIFI}:
            if dev_type in {NM_DEVICE_TYPE_WIFI}:
                self.log.debug("Network device found: %s", device_path)

                # Get access to PropertiesChanged signal
                dev_props_interface = dev_object.get_interface(
                    "org.freedesktop.DBus.Properties"
                )

                if dev_type == NM_DEVICE_TYPE_WIFI:
                    # Need to check for AP mode before looking at
                    # connectivity state.
                    #
                    # Otherwise, the Wi-Fi device reports itself as
                    # connected...to itself.
                    wireless_interface = dev_object.get_interface(
                        f"{NM_NAMESPACE}.Device.Wireless",
                    )

                    is_dev_connected = IsWifiConnected(
                        dev_interface, wireless_interface
                    )
                else:
                    # Just use device state for ethernet
                    is_dev_connected = IsDeviceConnected(dev_interface)

                network_devices.append((dev_props_interface, is_dev_connected))

        return network_devices

    def _dev_props_changed(
        self, _interface, _changed_props, _invalidated_props
    ):
        """Callback for properties changed signal"""
        if self._props_changed is not None:
            self._props_changed.set()


# -----------------------------------------------------------------------------


class IsWifiConnected:
    """Check if DBus Wi-Fi device is connected"""

    def __init__(self, dev_interface, wireless_interface):
        self.dev_interface = dev_interface
        self.wireless_interface = wireless_interface

    async def __call__(self):
        mode = await self.wireless_interface.get_mode()
        if mode == NM_802_11_MODE_INFRA:
            # Only check state if *not* in access point mode.
            # It will always report connected otherwise.
            state = await self.dev_interface.get_state()
            return state >= NETWORK_CONNECTED

        return False


class IsDeviceConnected:
    """Check if DBus network device is connected"""

    def __init__(self, dev_interface):
        self.dev_interface = dev_interface

    async def __call__(self):
        # Only check state
        state = await self.dev_interface.get_state()
        return state >= NETWORK_CONNECTED
