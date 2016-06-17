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

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self.register_apps()

        # self.register_regex("for (?P<SearchTerms>.*)")
        # self.register_regex("for (?P<SearchTerms>.*) on")

        roku_launch_intent = IntentBuilder("RokuLaunchIntent")\
            .require("RokuKeyword")\
            .require("RokuLaunchKeyword")\
            .require("Application")\
            .build()
        self.register_intent(roku_launch_intent, self.handle_roku_launch_intent)

        roku_home_intent = IntentBuilder("RokuHomeIntent")\
            .require("RokuKeyword")\
            .require("RokuHomeKeyword")\
            .build()
        self.register_intent(roku_home_intent, self.handle_roku_home_intent)

        roku_search_intent = IntentBuilder("RokuSearchIntent")\
            .require("RokuKeyword")\
            .require("RokuSearchKeyword")\
            .require("SearchTerms")\
            .optionally("Application")\
            .build()
        self.register_intent(roku_search_intent, self.handle_roku_search_intent)

        roku_apps_intent = IntentBuilder("RokuAppsIntent")\
            .require("RokuKeyword")\
            .require("RokuAppKeyword")\
            .build()
        self.register_intent(roku_apps_intent, self.handle_roku_apps_intent)

        roku_play_intent = IntentBuilder("RokuPlayIntent")\
            .require("RokuKeyword")\
            .require("RokuPlayKeyword")\
            .build()
        self.register_intent(roku_play_intent, self.handle_roku_play_intent)

    def register_apps(self):
        if self.roku:
            for app in self.roku.apps:
                self.register_vocabulary(app.name, "Application")

    def home_search(self, terms):
        if self.roku:
            self.roku.home()
            sleep(3)
            self.roku.down()
            self.roku.down()
            self.roku.down()
            self.roku.down()
            self.roku.down()
            self.roku.select()
            self.roku.literal(terms)
            sleep(2)
            self.roku.right()
            self.roku.right()
            self.roku.right()
            self.roku.right()
            self.roku.right()
            self.roku.right()
            sleep(.5)
            self.roku.select()

    def handle_roku_launch_intent(self, message):
        if self.roku:
            app = message.metadata.get('Application')
            self.speak_dialog("launch.app", {"Application": app})
            self.roku[app].launch()
        else:
            self.speak_dialog("no.device")

    def handle_roku_home_intent(self, message):
        if self.roku:
            self.speak_dialog("home")
            self.roku.home()
        else:
            self.speak_dialog("no.device")

    def handle_roku_search_intent(self, message):
        if self.roku:
            app = message.metadata.get('Application')
            terms = message.metadata.get('SearchTerms')

            self.speak_dialog("search.app", {"SearchTerms": terms})
            if app:
                if app == 'Netflix':
                    self.roku[app].launch()
                    sleep(3)
                    self.roku.up()
                    sleep(2)
                    self.roku.select()
                    self.roku.literal(terms)
            else:
                self.home_search(terms)
        else:
            self.speak_dialog("no.device")

    def handle_roku_apps_intent(self, message):
        if self.roku:
            self.speak_dialog("apps")
            for app in self.roku.apps:
                self.speak(app.name)
        else:
            self.speak_dialog("no.device")

    def handle_roku_play_intent(self, message):
        if self.roku:
            self.speak_dialog("play")
            self.roku.play()
        else:
            self.speak_dialog("no.device")
    def stop(self):
        pass


def create_skill():
    return RokuSkill()
