#!/usr/bin/env python3
import threading
import time

from mycroft.activity import Activity
from mycroft.messagebus import Message
from mycroft.util.network_utils import connected


class InternetConnectActivity(Activity):
    """Check for internet connectivity by trying to reach a website"""

    def started(self):
        self._connect_thread = threading.Thread(
            target=self._connect_proc, daemon=True
        )
        self._connect_thread.start()

    def _connect_proc(self):
        try:
            # Initial test
            is_connected = connected()

            if not is_connected:
                self.bus.emit(Message("hardware.internet-not-detected"))

            while not is_connected:
                is_connected = connected()
                time.sleep(1.0)

            self.bus.emit(Message("hardware.internet-detected"))
            self.log.info("Internet connection detected")
        except Exception:
            self.log.exception("error checking for internet connection")

    def ended(self):
        self._connect_thread.join(timeout=1.0)
