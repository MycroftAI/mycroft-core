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
"""Provide a common API for skills that define idle screen functionality.

The idle display should show when no other skill is using the display.  Some
skills use the display for a defined period of time before returning to the
idle display (e.g. Weather Skill).  Some skills take control of the display
indefinitely (e.g. Timer Skill).

The display could be a touch screen (such as on the Mark II), or an
Arduino LED array (such as on the Mark I), or any other type of display.  This
base class is meant to be agnostic to the type of display, with the
implementation details defined within the skill that uses this as a base class.
"""
from datetime import datetime, timedelta

from mycroft.messagebus import Message
from .mycroft_skill import MycroftSkill


class IdleDisplaySkill(MycroftSkill):
    """Base class for skills that define an idle display.

    An idle display is what shows on a device's screen when it is not in use
    by other skills.  For example, Mycroft's Home Screen Skill.
    """
    def initialize(self):
        """Tasks to complete during skill load but after bus initialization."""
        self._define_message_bus_handlers()

    def _define_message_bus_handlers(self):
        """Defines the bus events handled in this skill and their handlers."""
        self.bus.on("mycroft.ready", self.handle_mycroft_ready)

    def handle_mycroft_ready(self, _):
        """Shows idle screen when device is ready for use."""
        self._show_idle_screen()
        self.bus.emit(Message("skill.idle.displayed"))

    def _show_idle_screen(self):
        """Override this method to display the idle screen."""
        raise NotImplementedError(
            "Subclass must override the _show_idle_screen method"
        )
