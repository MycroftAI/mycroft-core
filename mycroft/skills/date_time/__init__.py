import datetime
from os.path import dirname, join

import tzlocal
from astral import Astral
from pytz import timezone

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill

__author__ = 'ryanleesipes'


# TODO - Localization
class TimeSkill(MycroftSkill):
    def __init__(self):
        super(TimeSkill, self).__init__(name="TimeSkill")
        self.format = self.config['time_format']

    def initialize(self):
        self.load_vocab_files(join(dirname(__file__), 'vocab', 'en-us'))

        self.register_regex("in (?P<Location>.*)")
        self.register_regex("at (?P<Location>.*)")

        intent = IntentBuilder("TimeIntent").require("TimeKeyword").optionally("Location").build()

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

    # This method only handles localtime, for other timezones the task falls to Wolfram.
    def handle_intent(self, message):
        location = message.metadata.get("Location", None)

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
