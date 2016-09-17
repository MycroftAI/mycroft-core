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

import tzlocal
from adapt.intent import IntentBuilder
from astral import Astral
from os.path import dirname, join
from pytz import timezone

from mycroft.skills.core import MycroftSkill

__author__ = 'ryanleesipes'


# TODO - Localization
class TimeSkill(MycroftSkill):
    def __init__(self):
        super(TimeSkill, self).__init__("TimeSkill")
        self.format = self.config['format']

    def initialize(self):
        self.load_vocab_files(join(dirname(__file__), 'vocab', 'en-us'))
        self.load_regex_files(join(dirname(__file__), 'regex', 'en-us'))

        intent = IntentBuilder("TimeIntent").require(
            "TimeKeyword").optionally("Location").build()

        self.register_intent(intent, self.handle_intent)

    def get_time_format(self, convert_time):

        if self.format == '12h':
            current_time = datetime.date.strftime(convert_time, "%I:%M, %p")
        else:
            current_time = datetime.date.strftime(convert_time, "%H:%M ")
        return current_time

    def get_timezone(self, locale):
        a = Astral()
        try:
            city = a[locale]
            return city.timezone
        except:
            return None

    # This method only handles localtime, for other timezones the task falls
    # to Wolfram.
    def handle_intent(self, message):
        location = message.data.get("Location", None)

        now = datetime.datetime.now(timezone('UTC'))
        if location is None:
            tz = tzlocal.get_localzone()
        else:
            astral_tz = self.get_timezone(location)
            tz = timezone(astral_tz) if astral_tz else None
            if not tz:
                self.speak("I could not find the timezone for " + location)
                return

        time_value = now.astimezone(tz)
        self.speak("It is currently " + self.get_time_format(time_value))

    def stop(self):
        pass


def create_skill():
    return TimeSkill()
