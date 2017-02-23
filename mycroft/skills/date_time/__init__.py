# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import datetime
from os.path import dirname

import tzlocal
from adapt.intent import IntentBuilder
from astral import Astral
from pytz import timezone

from mycroft.skills.core import MycroftSkill

__author__ = 'ryanleesipes', 'jdorleans'


# TODO - Localization
class TimeSkill(MycroftSkill):
    def __init__(self):
        super(TimeSkill, self).__init__("TimeSkill")
        self.astral = Astral()
        self.init_format()

    def init_format(self):
        if self.config_core.get('time_format') == 'full':
            self.format = "%H:%M"
        else:
            self.format = "%I:%M, %p"

    def initialize(self):
        intent = IntentBuilder("TimeIntent").require("QueryKeyword") \
            .require("TimeKeyword").optionally("Location").build()
        self.register_intent(intent, self.handle_intent)

    def get_timezone(self, locale):
        try:
            # This handles common city names, like "Dallas" or "Paris"
            return timezone(self.astral[locale].timezone)
        except:
            try:
                # This handles codes like "America/Los_Angeles"
                return timezone(locale)
            except:
                return None

    def handle_intent(self, message):
        location = message.data.get("Location")  # optional parameter
        nowUTC = datetime.datetime.now(timezone('UTC'))

        tz = self.get_timezone(self.location_timezone)
        if location:
            tz = self.get_timezone(location)

        if not tz:
            self.speak_dialog("time.tz.not.found", {"location": location})
            return

        # Convert UTC to appropriate timezone and format
        time = nowUTC.astimezone(tz).strftime(self.format)
        self.speak_dialog("time.current", {"time": time})

    def stop(self):
        pass


def create_skill():
    return TimeSkill()
