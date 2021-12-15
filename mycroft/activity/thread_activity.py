# Copyright 2021 Mycroft AI Inc.
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
"""Activity whose logic occurs in a separate thread"""
import threading
import typing

from mycroft.messagebus import Message
from mycroft.util import LOG

from .activity import Activity


class ThreadActivity(Activity):
    """Base class for activities"""

    def __init__(self, name: str, bus):
        super().__init__(name, bus)

        self._thread: typing.Optional[threading.Thread] = None
        self._block_event = threading.Event()

    def run(self, block: bool = True, timeout: typing.Optional[float] = None):
        """Runs activity, blocking by default until it ends"""
        self._block_event.clear()
        self._thread = threading.Thread(target=self._thread_proc, daemon=True)
        self._thread.start()

        if block:
            self._block_event.wait(timeout=timeout)

    def _thread_proc(self):
        """Runs activity inside thread"""
        try:
            self.bus.emit(Message(self._started_event))
            self._run()
        except Exception:
            LOG.exception("error in activity %s", self.name)
            end_data = dict(success=False)
        else:
            end_data = dict(success=True)

        self.bus.emit(Message(self._ended_event, end_data))
        self._block_event.set()
