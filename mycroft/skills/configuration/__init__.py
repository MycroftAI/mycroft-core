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


from adapt.intent import IntentBuilder
from os.path import dirname
from requests import HTTPError

from mycroft.api import DeviceApi
from mycroft.identity import IdentityManager
from mycroft.messagebus.message import Message
from mycroft.skills.scheduled_skills import ScheduledSkill
from mycroft.util.log import getLogger

__author__ = 'augustnmonteiro'

LOGGER = getLogger(__name__)


class ConfigurationSkill(ScheduledSkill):
    def __init__(self):
        super(ConfigurationSkill, self).__init__("ConfigurationSkill")
        self.max_delay = self.config.get('max_delay')

    def initialize(self):
        self.load_data_files(dirname(__file__))
        intent = IntentBuilder("UpdateConfigurationIntent") \
            .require("ConfigurationSkillKeyword") \
            .require("ConfigurationSkillUpdateVerb") \
            .build()
        self.register_intent(intent, self.handle_update_intent)
        self.schedule()

    def handle_update_intent(self, message):
        try:
            self.update_config()
            self.speak_dialog("config.updated")
        except HTTPError as e:
            self.__api_error(e)

    def notify(self, timestamp):
        try:
            self.update_config()
        except HTTPError as e:
            LOGGER.warn("Error on update settings '%s'", e)
        self.schedule()

    def update_config(self):
        config = DeviceApi().find_setting()
        self.emitter.emit(Message("configuration.updated", config))

    def __api_error(self, e):
        if e.response.status_code == 401:
            LOGGER.warn("Access Denied at mycroft.ai")
            self.emitter.emit(Message("mycroft.not.paired"))


    def get_times(self):
        return [self.get_utc_time() + self.max_delay]

    def stop(self):
        pass


def create_skill():
    return ConfigurationSkill()
