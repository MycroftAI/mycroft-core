#!/usr/bin/env python3
import threading
import time
import typing

from mycroft.activity import Activity
from mycroft.messagebus import Message
from mycroft.util.network_utils import connected


class InternetConnectActivity(Activity):
    """Check for internet connectivity by trying to reach a website"""

    def __init__(self, name: str, bus):
        super().__init__(name, bus)

        self._connect_thread: typing.Optional[threading.Thread] = None

    def started(self):
        self._connect_thread = threading.Thread(
            target=self._connect_proc, daemon=True
        )
        self._connect_thread.start()

    def ended(self):
        if self._connect_thread is not None:
            self._connect_thread.join(timeout=1.0)
            self._connect_thread = None

    def _connect_proc(self):
        try:
            # Initial test
            is_connected = connected()

            if not is_connected:
                self.bus.emit(Message("hardware.internet-not-detected"))
                self.log.info("Internet connection not detected")

            while not is_connected:
                is_connected = connected()
                time.sleep(1.0)

            self.bus.emit(Message("hardware.internet-detected"))
            self.log.info("Internet connection detected")
        except Exception as error:
            self.log.exception("error checking for internet connection")
            self.bus.emit(
                Message(f"{self.name}.error", data={"error": str(error)})
            )

        self.end()
