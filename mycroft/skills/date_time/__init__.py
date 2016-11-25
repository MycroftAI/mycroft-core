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
from os.path import dirname, join

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
        self.format = self.init_format()

    def init_format(self):
        if self.config_core.get('time_format', 'half') == 'half':
            return "%I:%M, %p"
        return "%H:%M"

    def initialize(self):
        self.load_data_files(dirname(__file__))
        intent = IntentBuilder("TimeIntent").require("TimeKeyword") \
            .optionally("Location").build()
        self.register_intent(intent, self.handle_intent)

    def get_timezone(self, locale):
        try:
            return timezone(self.astral[locale].timezone)
        except:
            return None

    # This method only handles localtime, for other timezones the task falls
    # to Wolfram.
    def handle_intent(self, message):
        location = message.data.get("Location")
        now = datetime.datetime.now(timezone('UTC'))
        tz = tzlocal.get_localzone()
        if location:
            tz = self.get_timezone(location)
            if not tz:
                self.speak_dialog("time.tz.not.found", {"location": location})
                return
        time = now.astimezone(tz).strftime(self.format)
        self.speak_dialog("time.current", {"time": time})

    def stop(self):
        pass


def create_skill():
    return TimeSkill()
