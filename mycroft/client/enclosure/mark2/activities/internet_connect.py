#!/usr/bin/env python3
import time

from mycroft.activity import ThreadActivity
from mycroft.messagebus import Message
from mycroft.util.network_utils import connected

NOT_DETECTED_RETRIES = 1


class InternetConnectActivity(ThreadActivity):
    """Check for internet connectivity by trying to reach a website"""

    def started(self):
        try:
            # Initial test
            for _ in range(NOT_DETECTED_RETRIES):
                is_connected = connected()
                if is_connected:
                    break

                time.sleep(1.0)

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
