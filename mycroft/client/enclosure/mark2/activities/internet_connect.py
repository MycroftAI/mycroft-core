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
"""Checks for internet connectivity"""
import time

from mycroft.activity import Activity
from mycroft.messagebus import Message
from mycroft.util.log import LOG
from mycroft.util.network_utils import connected

NOT_DETECTED_RETRIES = 1


class InternetConnectActivity(Activity):
    """Check for internet connectivity by trying to reach a website"""

    def _run(self):
        for _ in range(NOT_DETECTED_RETRIES):
            is_connected = connected()
            if is_connected:
                break

            time.sleep(1.0)

        if not is_connected:
            self.bus.emit(Message("hardware.internet-not-detected"))
            LOG.info("Internet connection not detected")

        while not is_connected:
            is_connected = connected()
            time.sleep(1.0)

        self.bus.emit(Message("hardware.internet-detected"))
        LOG.info("Internet connection detected")
