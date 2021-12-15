#!/usr/bin/env python3
import time

from mycroft.activity import Activity
from mycroft.messagebus import Message
from mycroft.util.log import LOG
from mycroft.util.network_utils import check_system_clock_sync_status


class SystemClockSyncActivity(Activity):
    """Waits for the system clock to be synchronized with a NTP service."""

    def _run(self):
        check_count = 0
        while True:
            clock_synchronized = check_system_clock_sync_status()
            if clock_synchronized:
                LOG.info("System clock synchronized")
                self.bus.emit(Message("hardware.clock-synchronized"))
                break

            if (check_count % 60) == 0:
                LOG.info("Waiting for system clock to synchronize...")

            check_count += 1
            time.sleep(1)
