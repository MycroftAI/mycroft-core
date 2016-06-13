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


from os.path import dirname
import nest
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'crios'

LOGGER = getLogger(__name__)


class NestSkill(MycroftSkill):
    def __init__(self):
        super(NestSkill, self).__init__(name="NestSkill")
        self.nest_user = self.config.get('nest_user')
        self.nest_password = self.config.get('nest_password')

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self.register_regex("(?P<NestTemperature>\d+)")

        nest_intent = IntentBuilder("NestIntent")\
            .require("NestKeyword").require("NestTemperature").build()
        self.register_intent(nest_intent, self.handle_nest_intent)

    def handle_nest_intent(self, message):
        try:
            temperature = message.metadata.get("NestTemperature", None)
            LOGGER.debug(temperature)
            napi = nest.Nest(self.nest_user, self.nest_password)
            print "ASDFASDFASDF" + temperature
            with nest.Nest(self.nest_user, self.nest_password) as napi:
             for device in napi.devices:
              device.temperature = temperature
            self.speak_dialog('nest.set', data={'NestTemperature': temperature})
        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def stop(self):
        pass


def create_skill():
    return NestSkill()
