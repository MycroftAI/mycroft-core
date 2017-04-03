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
import subprocess

from os.path import dirname, join

from adapt.intent import IntentBuilder

from mycroft import MYCROFT_ROOT_PATH
from mycroft.configuration import ConfigurationManager
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'augustnmonteiro2'

logger = getLogger(__name__)

config = ConfigurationManager.get().get("SkillInstallerSkill")

BIN = config.get("path", join(MYCROFT_ROOT_PATH, 'msm', 'msm'))


class SkillInstallerSkill(MycroftSkill):
    def __init__(self):
        super(SkillInstallerSkill, self).__init__(name="SkillInstallerSkill")

    def initialize(self):
        install = IntentBuilder("InstallIntent"). \
            require("InstallKeyword").build()
        self.register_intent(install, self.install)

    def install(self, message):
        utterance = message.data.get('utterance').lower()
        skill = utterance.replace(message.data.get('InstallKeyword'), '')
        p = subprocess.Popen(
            [BIN, "install", skill.strip().replace(" ", "-")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        text, err = p.communicate()
        if text.splitlines()[1] == "Your search has multiple choices":
            stdout = text.splitlines()
            del stdout[0:3]
            self.speak_dialog("choose", data={'skills': ", ".join(stdout)})
        elif text.splitlines()[1] == "Skill not found" or skill == "":
            self.speak_dialog("not.found", data={'skill': skill})
        elif text.splitlines()[2] == "Skill installed!":
            self.speak_dialog("installed", data={'skill': skill})

    def stop(self):
        pass


def create_skill():
    return SkillInstallerSkill()
