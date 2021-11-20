# Copyright 2017 Mycroft AI Inc.
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

"""Events with respect for montonic time.

The MontonicEvent class defined here wraps the normal class ensuring that
changes in system time are handled.
"""
from threading import Event
from time import sleep, monotonic

from mycroft.util.log import LOG


class MonotonicEvent(Event):
    """Event class with monotonic timeout.

    Normal Event doesn't do wait timeout in a monotonic manner and may be
    affected by changes in system time. This class wraps the Event class
    wait() method with logic guards ensuring monotonic operation.
    """

    def wait_timeout(self, timeout):
        """Handle timeouts in a monotonic way.

        Repeatingly wait as long the event hasn't been set and the
        monotonic time doesn't indicate a timeout.

        Args:
            timeout: timeout of wait in seconds

        Returns:
            True if Event has been set, False if timeout expired
        """
        result = False
        end_time = monotonic() + timeout

        while not result and (monotonic() < end_time):
            # Wait however many seconds are left until the timeout has passed
            sleep(0.1)  # Mainly a precaution to not busy wait
            remaining_time = end_time - monotonic()
            LOG.debug('Will wait for {} sec for Event'.format(remaining_time))
            result = super().wait(remaining_time)

        return result

    def wait(self, timeout=None):
        if timeout is None:
            ret = super().wait()
        else:
            ret = self.wait_timeout(timeout)
        return ret
