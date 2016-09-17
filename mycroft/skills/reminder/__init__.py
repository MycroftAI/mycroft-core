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


import time
from alsaaudio import Mixer
from datetime import datetime, timedelta

import re
import yaml
from adapt.intent import IntentBuilder
from os.path import dirname

from mycroft.skills.scheduled_skills import ScheduledCRUDSkill

__author__ = 'jdorleans'


# TODO - Localization, Sandbox
class ReminderSkill(ScheduledCRUDSkill):
    PRONOUNS = {'i': 'you', 'me': 'you', 'my': 'your', 'myself': 'yourself',
                'am': 'are', "'m": "are", "i'm": "you're"}

    def __init__(self):
        super(ReminderSkill, self).__init__(
            "ReminderSkill", None, dirname(__file__))
        self.reminder_on = False
        self.max_delay = self.config.get('max_delay')
        self.repeat_time = self.config.get('repeat_time')
        self.extended_delay = self.config.get('extended_delay')

    def initialize(self):
        super(ReminderSkill, self).initialize()
        intent = IntentBuilder(
            'ReminderSkillStopIntent').require('ReminderSkillStopVerb') \
            .require('ReminderSkillKeyword').build()
        self.register_intent(intent, self.__handle_stop)

    def load_data(self):
        try:
            with self.file_system.open(self.PENDING_TASK, 'r') as f:
                self.data = yaml.safe_load(f)
                assert self.data
        except:
            self.data = {}

    def load_repeat_data(self):
        try:
            with self.file_system.open(self.REPEAT_TASK, 'r') as f:
                self.repeat_data = yaml.safe_load(f)
                assert self.repeat_data
        except:
            self.repeat_data = {}

    def __handle_stop(self, message):
        if self.reminder_on:
            self.speak_dialog('reminder.off')
        self.reminder_on = False

    def notify(self, timestamp):
        with self.LOCK:
            if self.data.__contains__(timestamp):
                volume = None
                self.reminder_on = True
                delay = self.__calculate_delay(self.max_delay)

                while self.reminder_on and datetime.now() < delay:
                    self.speak_dialog(
                        'reminder.notify',
                        data=self.build_feedback_payload(timestamp))
                    time.sleep(1)
                    self.speak_dialog('reminder.stop')
                    time.sleep(self.repeat_time)
                    if not volume and datetime.now() >= delay:
                        mixer = Mixer()
                        volume = mixer.getvolume()[0]
                        mixer.setvolume(100)
                        delay = self.__calculate_delay(self.extended_delay)
                if volume:
                    Mixer().setvolume(volume)
                self.remove(timestamp)
                self.reminder_on = False
                self.save()

    @staticmethod
    def __calculate_delay(seconds):
        return datetime.now() + timedelta(seconds=seconds)

    def add(self, date, message):
        utterance = message.data.get('utterance').lower()
        utterance = utterance.replace(
            message.data.get('ReminderSkillCreateVerb'), '')
        utterance = self.__fix_pronouns(utterance)
        self.repeat_data[date] = self.time_rules.get_week_days(utterance)
        self.data[date] = self.__remove_time(utterance).strip()

    def __fix_pronouns(self, utterance):
        msg = utterance.strip()
        for key, val in self.PRONOUNS.iteritems():
            k = key.lower()
            v = val.lower()
            msg = msg.replace(' ' + k + ' ', ' ' + v + ' ')
            msg = re.sub('^' + key + ' ', val + ' ', msg)
            msg = re.sub(' ' + key + '$', ' ' + val, msg)
        return msg

    def __remove_time(self, utterance):
        pos = (0, 0)
        for regex in self.time_rules.rules.get('time_regex'):
            pattern = re.compile(regex, re.IGNORECASE)
            result = pattern.search(utterance)
            if result:
                span = result.span()
                if (pos[1] - pos[0]) < (span[1] - span[0]):
                    pos = span
        msg = utterance[:pos[0]] + utterance[pos[1]:]
        if pos[0] != pos[1]:
            msg = self.__remove_time(msg)
        return msg

    def save(self):
        with self.file_system.open(self.PENDING_TASK, 'w') as f:
            yaml.safe_dump(self.data, f)
        with self.file_system.open(self.REPEAT_TASK, 'w') as f:
            yaml.safe_dump(self.repeat_data, f)
        self.schedule()

    def stop(self):
        self.__handle_stop(None)


def create_skill():
    return ReminderSkill()
