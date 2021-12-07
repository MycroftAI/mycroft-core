#!/usr/bin/env python3
import asyncio
import threading

from dbus_next import BusType
from dbus_next.aio import MessageBus

from mycroft.activity import Activity
from mycroft.messagebus import Message

# Network manager state
# https://developer-old.gnome.org/NetworkManager/stable/nm-dbus-types.html#NMState

NOT_CONNECTED = 0
NETWORK_CONNECTED = 50

NM_NAMESPACE = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"


class NetworkConnectActivity(Activity):
    """Determines network connectivity using DBus NetworkManager"""

    def started(self):
        self._async_thread = threading.Thread(
            target=self._activity_proc, daemon=True
        )
        self._async_thread.start()

    def ended(self):
        self._async_thread.join(timeout=1.0)

    def _activity_proc(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._activity_proc_async())
        self._loop.close()

    async def _activity_proc_async(self):
        self._state_ready = asyncio.Event()
        self._nm_state = NOT_CONNECTED

        try:
            self.dbus = MessageBus(bus_type=BusType.SYSTEM)
            await self.dbus.connect()

            nm_interface = await self._get_network_manager()

            # Get initial state
            self._nm_state = await nm_interface.get_state()

            # Subscribe to state updates
            nm_interface.on_state_changed(self._nm_state_changed)

            if not self._is_connected():
                self.bus.emit(Message("hardware.network-not-detected"))

            # Wait until connected
            while not self._is_connected():
                await self._state_ready.wait()

            # Remove signal handler
            nm_interface.off_state_changed(self._nm_state_changed)

            self.bus.emit(Message("hardware.network-detected"))
            self.log.info("Network connection detected")

            await self.dbus.wait_for_disconnect()
        except Exception:
            self.log.exception("error while checking for network connectivity")

    def _is_connected(self):
        """True if NetworkManager state is at least locally connected"""
        return self._nm_state >= NETWORK_CONNECTED

    def _nm_state_changed(self, new_state: int):
        """Callback for state changed signal"""
        self._nm_state = new_state
        self._state_ready.set()

    async def _get_network_manager(self):
        """Get DBus interface to NetworkManager"""
        introspection = await self.dbus.introspect(NM_NAMESPACE, NM_PATH)

        nm_object = self.dbus.get_proxy_object(
            NM_NAMESPACE,
            NM_PATH,
            introspection,
        )

        return nm_object.get_interface(NM_NAMESPACE)
