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


import abc
from datetime import datetime
from threading import Timer, Lock
from time import mktime

import parsedatetime as pdt
from adapt.intent import IntentBuilder

from mycroft.skills import time_rules
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

logger = getLogger(__name__)


class ScheduledSkill(MycroftSkill):
    """
    Abstract class which provides a repeatable notification behaviour at a
    specified time.

    Skills implementation inherits this class when it needs to schedule a task
    or a notification.
    """

    DELTA_TIME = int((datetime.now() - datetime.utcnow()).total_seconds())
    SECONDS_PER_DAY = 86400
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_MINUTE = 60

    def __init__(self, name, emitter=None):
        super(ScheduledSkill, self).__init__(name, emitter)
        self.timer = None
        self.calendar = pdt.Calendar()
        self.time_rules = time_rules.create(self.lang)

    def schedule(self):
        times = sorted(self.get_times())

        if len(times) > 0:
            self.cancel()
            t = times[0]
            now = self.get_utc_time()
            delay = max(float(t) - now, 1)
            self.timer = Timer(delay, self.notify, [t])
            self.start()

    def start(self):
        if self.timer:
            self.timer.start()

    def cancel(self):
        if self.timer:
            self.timer.cancel()

    def convert_local(self, utc_time):
        return utc_time + self.DELTA_TIME

    def get_utc_time(self, sentence=''):
        return mktime(self.calendar.parse(sentence)[0]) - self.DELTA_TIME

    def get_formatted_time(self, timestamp):
        date = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        diff = (date - now).total_seconds()
        if diff <= self.SECONDS_PER_DAY:
            hours, remainder = divmod(diff, self.SECONDS_PER_HOUR)
            minutes, seconds = divmod(remainder, self.SECONDS_PER_MINUTE)
            if hours:
                return "%s hours and %s minutes from now" % \
                       (int(hours), int(minutes))
            else:
                return "%s minutes and %s seconds from now" % \
                       (int(minutes), int(seconds))
        dt_format = self.config_core.get('date_format')
        dt_format += " at " + self.config_core.get('time_format')
        return date.strftime(dt_format)

    @abc.abstractmethod
    def get_times(self):
        pass

    @abc.abstractmethod
    def notify(self, timestamp):
        pass


class ScheduledCRUDSkill(ScheduledSkill):
    """
    Abstract CRUD class which provides a repeatable notification behaviour at
    a specified time.

    It registers CRUD intents and exposes its functions to manipulate a
    provided ``data``

    Skills implementation inherits this class when it needs to schedule a task
    or a notification with a provided data
    that can be manipulated by CRUD commands.

    E.g. CRUD operations for a Reminder Skill
        #. "Mycroft, list two reminders"
        #. "Mycroft, list all reminders"
        #. "Mycroft, delete one reminder"
        #. "Mycroft, remind me to contribute to Mycroft project"
    """

    LOCK = Lock()
    REPEAT_TASK = 'repeat'
    PENDING_TASK = 'pending'
    ONE_DAY_SECS = 86400

    def __init__(self, name, emitter=None, basedir=None):
        super(ScheduledCRUDSkill, self).__init__(name, emitter)
        self.data = {}
        self.repeat_data = {}
        self.basedir = basedir

    def initialize(self):
        self.load_data()
        self.load_repeat_data()
        self.load_data_files(self.basedir)
        self.register_regex("(?P<" + self.name + "Amount>\d+)")
        self.register_intent(
            self.build_intent_create().build(), self.handle_create)
        self.register_intent(
            self.build_intent_list().build(), self.handle_list)
        self.register_intent(
            self.build_intent_delete().build(), self.handle_delete)
        self.schedule()

    @abc.abstractmethod
    def load_data(self):
        pass

    @abc.abstractmethod
    def load_repeat_data(self):
        pass

    def build_intent_create(self):
        return IntentBuilder(
            self.name + 'CreateIntent').require(self.name + 'CreateVerb')

    def build_intent_list(self):
        return IntentBuilder(
            self.name + 'ListIntent').require(self.name + 'ListVerb') \
            .optionally(self.name + 'Amount').require(self.name + 'Keyword')

    def build_intent_delete(self):
        return IntentBuilder(
            self.name + 'DeleteIntent').require(self.name + 'DeleteVerb') \
            .optionally(self.name + 'Amount').require(self.name + 'Keyword')

    def get_times(self):
        return self.data.keys()

    def handle_create(self, message):
        utterance = message.data.get('utterance')
        date = self.get_utc_time(utterance)
        delay = date - self.get_utc_time()

        if delay > 0:
            self.feedback_create(date)
            self.add_sync(date, message)
            self.save_sync()
        else:
            self.speak_dialog('schedule.datetime.error')

    def feedback_create(self, utc_time):
        self.speak_dialog(
            'schedule.create', data=self.build_feedback_payload(utc_time))

    def add_sync(self, utc_time, message):
        with self.LOCK:
            self.add(utc_time, message)

    def add(self, utc_time, message):
        utterance = message.data.get('utterance')
        self.data[utc_time] = None
        self.repeat_data[utc_time] = self.time_rules.get_week_days(utterance)

    def remove_sync(self, utc_time, add_next=True):
        with self.LOCK:
            val = self.remove(utc_time, add_next)
        return val

    def remove(self, utc_time, add_next=True):
        value = self.data.pop(utc_time)
        self.add_next_time(utc_time, value, add_next)
        return value

    def add_next_time(self, utc_time, value, add_next=True):
        days = self.repeat_data.pop(utc_time)
        if add_next and days:
            now_time = self.get_utc_time()
            next_time = utc_time + self.ONE_DAY_SECS
            now_day = datetime.fromtimestamp(utc_time).weekday()
            next_day = datetime.fromtimestamp(next_time).weekday()
            while next_day != now_day:
                if days[next_day] and next_time >= now_time:
                    self.data[next_time] = value
                    self.repeat_data[next_time] = days
                    break
                next_time += self.ONE_DAY_SECS
                next_day = datetime.fromtimestamp(next_time).weekday()

    def save_sync(self):
        with self.LOCK:
            self.save()

    @abc.abstractmethod
    def save(self):
        pass

    def handle_list(self, message):
        count = self.get_amount(message)
        if count > 0:
            for key in sorted(self.data.keys()):
                if count > 0:
                    self.feedback_list(key)
                    count -= 1
                else:
                    break
        else:
            self.speak_dialog('schedule.list.empty')

    def feedback_list(self, utc_time):
        self.speak_dialog(
            'schedule.list', data=self.build_feedback_payload(utc_time))

    def build_feedback_payload(self, utc_time):
        timestamp = self.convert_local(float(utc_time))
        payload = {
            'data': self.data.get(utc_time),
            'datetime': self.get_formatted_time(timestamp)
        }
        return payload

    def handle_delete(self, message):
        count = self.get_amount(message)
        if count > 0:
            amount = count
            for key in sorted(self.data.keys()):
                if count > 0:
                    self.remove_sync(key, False)
                    count -= 1
                else:
                    break
            self.feedback_delete(amount)
            self.save_sync()
        else:
            self.speak_dialog('schedule.delete.empty')

    def feedback_delete(self, amount):
        if amount > 1:
            self.speak_dialog('schedule.delete.many', data={'amount': amount})
        else:
            self.speak_dialog(
                'schedule.delete.single', data={'amount': amount})

    # TODO - Localization
    def get_amount(self, message, default=None):
        size = len(self.data)
        amount = message.data.get(self.name + 'Amount', default)
        if amount in ['all', 'my', 'all my', None]:
            total = size
        elif amount in ['one', 'the next', 'the following']:
            total = 1
        elif amount == 'two':
            total = 2
        else:
            total = int(amount)
        return min(total, size)
