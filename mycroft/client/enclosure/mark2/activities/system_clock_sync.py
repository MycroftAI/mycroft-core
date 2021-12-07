#!/usr/bin/env python3
import threading
import time

from mycroft.activity import Activity
from mycroft.messagebus import Message
from mycroft.util.network_utils import check_system_clock_sync_status


class SystemClockSyncActivity(Activity):
    """Waits for the system clock to be synchronized with a NTP service."""

    def started(self):
        self._sync_thread = threading.Thread(
            target=self._sync_proc, daemon=True
        )
        self._sync_thread.start()

    def _sync_proc(self):
        try:
            check_count = 0
            while True:
                clock_synchronized = check_system_clock_sync_status()
                if clock_synchronized:
                    self.log.info("System clock synchronized")
                    self.bus.emit(Message("hardware.clock-synchronized"))
                    break

                if (check_count % 60) == 0:
                    self.log.info("Waiting for system clock to synchronize...")

                check_count += 1
                time.sleep(1)
        except Exception:
            self.log.exception("error synchronizing system clock")

        self.end()

    def ended(self):
        self._sync_thread.join(timeout=1.0)
