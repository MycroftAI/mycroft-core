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
"""
NOTE: this is dead code! do not use!

This file is only present to ensure backwards compatibility
in case someone is importing from here

This is only meant for 3rd party code expecting ovos-core
to be a drop in replacement for mycroft-core

TODO: consider importing from PHAL if it's compatible
"""


class EnclosureArduino:
    """
    Listens to enclosure commands for Mycroft's Arduino.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, bus, writer):
        self.bus = bus
        self.writer = writer
        self.__init_events()

    def __init_events(self):
        self.bus.on('enclosure.system.reset', self.reset)
        self.bus.on('enclosure.system.mute', self.mute)
        self.bus.on('enclosure.system.unmute', self.unmute)
        self.bus.on('enclosure.system.blink', self.blink)

    def reset(self, event=None):
        self.writer.write("system.reset")

    def mute(self, event=None):
        self.writer.write("system.mute")

    def unmute(self, event=None):
        self.writer.write("system.unmute")

    def blink(self, event=None):
        times = 1
        if event and event.data:
            times = event.data.get("times", times)
        self.writer.write("system.blink=" + str(times))
