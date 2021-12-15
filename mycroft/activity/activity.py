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
"""Base class for activites.

An activity is some action that occurs between a started and ended event.
"""
import abc

from mycroft.messagebus import Message
from mycroft.util import LOG


class Activity(abc.ABC):
    """Base class for activities"""

    def __init__(self, name: str, bus):
        self.name = name
        self.bus = bus

        self._started_event = f"{self.name}.started"
        self._ended_event = f"{self.name}.ended"

    def run(self):
        """Runs activity"""
        self.bus.emit(Message(self._started_event))
        try:
            self._run()
        except Exception:
            LOG.exception("error in activity %s", self.name)
            end_data = dict(success=False)
        else:
            end_data = dict(success=True)

        self.bus.emit(Message(self._ended_event, end_data))

    @abc.abstractmethod
    def _run(self):
        """Override to add activity logic"""
        pass
