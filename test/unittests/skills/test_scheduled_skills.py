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
#
import unittest
from datetime import datetime, timedelta

from mycroft.skills.scheduled_skills import ScheduledSkill


class ScheduledSkillTest(unittest.TestCase):
    skill = ScheduledSkill(name='ScheduledSkillTest')

    def test_formatted_time_today_hours(self):
        date = datetime.now() + timedelta(hours=2)
        self.assertEquals(self.skill.
                          get_formatted_time(float(date.strftime('%s'))),
                          "1 hours and 59 minutes from now")

    def test_formatted_time_today_min(self):
        date = datetime.now() + timedelta(minutes=2)
        self.assertEquals(self.skill.
                          get_formatted_time(float(date.strftime('%s'))),
                          "1 minutes and 59 seconds from now")

    def test_formatted_time_days(self):
        self.skill.config_core = {}
        self.skill.config_core['time_format'] = 'full'
        self.skill.config_core['date_format'] = 'DMY'
        self.skill.init_format()

        date = datetime.now() + timedelta(days=2)
        self.assertEquals(self.skill.
                          get_formatted_time(float(date.strftime('%s'))),
                          date.strftime("%d %B, %Y at %H:%M"))

        self.skill.config_core['date_format'] = 'MDY'
        self.skill.init_format()

        date = datetime.now() + timedelta(days=2)
        self.assertEquals(self.skill.
                          get_formatted_time(float(date.strftime('%s'))),
                          date.strftime("%B %d, %Y at %H:%M"))
