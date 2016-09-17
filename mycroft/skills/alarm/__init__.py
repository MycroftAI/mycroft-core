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

import yaml
from adapt.intent import IntentBuilder
from os.path import dirname, join

from mycroft.skills.scheduled_skills import ScheduledCRUDSkill
from mycroft.util import play_mp3

__author__ = 'jdorleans'


# TODO - Localization
class AlarmSkill(ScheduledCRUDSkill):
    def __init__(self):
        super(AlarmSkill, self).__init__("AlarmSkill", None, dirname(__file__))
        self.alarm_on = False
        self.max_delay = self.config.get('max_delay')
        self.repeat_time = self.config.get('repeat_time')
        self.extended_delay = self.config.get('extended_delay')
        self.file_path = join(self.basedir, self.config.get('filename'))

    def initialize(self):
        super(AlarmSkill, self).initialize()
        intent = IntentBuilder(
            'AlarmSkillStopIntent').require('AlarmSkillStopVerb') \
            .require('AlarmSkillKeyword').build()
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
        if self.alarm_on:
            self.speak_dialog('alarm.off')
        self.alarm_on = False

    def notify(self, timestamp):
        with self.LOCK:
            if self.data.__contains__(timestamp):
                volume = None
                self.alarm_on = True
                delay = self.__calculate_delay(self.max_delay)

                while self.alarm_on and datetime.now() < delay:
                    play_mp3(self.file_path)
                    time.sleep(2)
                    self.speak_dialog('alarm.stop')
                    time.sleep(self.repeat_time + 2)
                    if not volume and datetime.now() >= delay:
                        mixer = Mixer()
                        volume = mixer.getvolume()[0]
                        mixer.setvolume(100)
                        delay = self.__calculate_delay(self.extended_delay)
                if volume:
                    Mixer().setvolume(volume)
                self.remove(timestamp)
                self.alarm_on = False
                self.save()

    @staticmethod
    def __calculate_delay(seconds):
        return datetime.now() + timedelta(seconds=seconds)

    def save(self):
        with self.file_system.open(self.PENDING_TASK, 'w') as f:
            yaml.safe_dump(self.data, f)
        with self.file_system.open(self.REPEAT_TASK, 'w') as f:
            yaml.safe_dump(self.repeat_data, f)
        if not self.alarm_on:
            self.schedule()

    def stop(self):
        self.__handle_stop(None)


def create_skill():
    return AlarmSkill()
