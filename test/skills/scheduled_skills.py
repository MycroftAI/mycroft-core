from datetime import datetime, timedelta
import unittest

from mycroft.skills.scheduled_skills import ScheduledSkill
from mycroft.util.log import getLogger

__author__ = 'eward'

logger = getLogger(__name__)


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
