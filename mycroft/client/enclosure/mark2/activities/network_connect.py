#!/usr/bin/env python3
import asyncio
import threading
import typing

from mycroft.activity import Activity
from mycroft.messagebus import Message
from mycroft.util.network_utils import get_dbus, get_network_manager

# Network manager state
# https://developer-old.gnome.org/NetworkManager/stable/nm-dbus-types.html#NMState

NOT_CONNECTED = 0
NETWORK_CONNECTED = 50


class NetworkConnectActivity(Activity):
    """Determines network connectivity using DBus NetworkManager"""

    def __init__(
        self, name: str, bus, bus_address: typing.Optional[str] = None
    ):
        super().__init__(name, bus)

        self._bus_address = bus_address
        self._async_thread: typing.Optional[threading.Thread] = None
        self._nm_state: int = NOT_CONNECTED
        self._state_ready: typing.Optional[asyncio.Event] = None

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
        self._state_ready = asyncio.Event()

        try:
            dbus = get_dbus()
            await dbus.connect()

            nm_interface = await get_network_manager(dbus)

            # Subscribe to state updates
            nm_interface.on_state_changed(self._nm_state_changed)

            # Get initial state
            self._nm_state = await nm_interface.get_state()

            if not self._is_connected():
                self.bus.emit(Message("hardware.network-not-detected"))
                self.log.info("Network connection not detected")

            # Wait until connected
            while not self._is_connected():
                await self._state_ready.wait()

            # Remove signal handler
            nm_interface.off_state_changed(self._nm_state_changed)

            self.bus.emit(Message("hardware.network-detected"))
            self.log.info("Network connection detected")

            await dbus.wait_for_disconnect()
        except Exception as error:
            self.log.exception("error while checking for network connectivity")
            self.bus.emit(
                Message(f"{self.name}.error", data={"error": str(error)})
            )

    def _is_connected(self):
        """True if NetworkManager state is at least locally connected"""
        return self._nm_state >= NETWORK_CONNECTED

    def _nm_state_changed(self, new_state: int):
        """Callback for state changed signal"""
        self._nm_state = new_state

        if self._state_ready is not None:
            self._state_ready.set()
