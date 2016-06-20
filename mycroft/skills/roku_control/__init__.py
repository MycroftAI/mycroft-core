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

from roku import Roku
from adapt.intent import IntentBuilder
from os.path import dirname
from time import sleep

from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'eward'

logger = getLogger(__name__)


class RokuSkill(MycroftSkill):
    def __init__(self):
        super(RokuSkill, self).__init__(name="RokuSkill")
        self.ip = str(self.config['ip'])
        self.roku = None
        if self.ip:
            self.roku = Roku(self.ip)
        else:
            raise ValueError("There is no Roku device in the configuration files.")

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self.register_apps()

        roku_launch_intent = IntentBuilder("RokuLaunchIntent")\
            .require("RokuKeyword")\
            .require("RokuLaunchKeyword")\
            .require("Application")\
            .build()
        self.register_intent(roku_launch_intent,
                             self.handle_roku_launch_intent)

        roku_home_intent = IntentBuilder("RokuHomeIntent")\
            .require("RokuKeyword")\
            .require("RokuHomeKeyword")\
            .build()
        self.register_intent(roku_home_intent,
                             self.handle_roku_home_intent)

        roku_apps_intent = IntentBuilder("RokuAppsIntent")\
            .require("RokuKeyword")\
            .require("RokuAppKeyword")\
            .build()
        self.register_intent(roku_apps_intent,
                             self.handle_roku_apps_intent)

        roku_play_intent = IntentBuilder("RokuPlayIntent")\
            .require("RokuKeyword")\
            .require("RokuPlayKeyword")\
            .build()
        self.register_intent(roku_play_intent,
                             self.handle_roku_play_intent)

        roku_pause_intent = IntentBuilder("RokuPauseIntent")\
            .require("RokuKeyword")\
            .require("RokuPauseKeyword")\
            .build()
        self.register_intent(roku_pause_intent,
                             self.handle_roku_pause_intent)

    def register_apps(self):
        for app in self.roku.apps:
            self.register_vocabulary(app.name, "Application")

    def handle_roku_launch_intent(self, message):
        app = message.metadata.get('Application')
        self.speak_dialog("launch.app", {"application": app})
        self.roku[app].launch()

    def handle_roku_home_intent(self, message):
        self.speak_dialog("home")
        self.roku.home()

    def handle_roku_apps_intent(self, message):
        self.speak_dialog("apps")
        for app in self.roku.apps:
            self.speak(app.name)

    def handle_roku_play_intent(self, message):
        self.speak_dialog("play")
        self.roku.play()

    def handle_roku_pause_intent(self, message):
        self.speak_dialog("pause")
        self.roku.play()

    def stop(self):
        pass


def create_skill():
    return RokuSkill()
