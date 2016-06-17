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


from os.path import dirname, join
import re

from netifaces import interfaces, ifaddresses, AF_INET

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

logger = getLogger(__name__)

__author__ = 'ryanleesipes'


class IPSkill(MycroftSkill):
    def __init__(self):
        super(IPSkill, self).__init__(name="IPSkill")

    def initialize(self):
        self.load_vocab_files(join(dirname(__file__), 'vocab', 'en-us'))

        intent = IntentBuilder("IPIntent").require("IPCommand").build()
        self.register_intent(intent, self.handle_intent)

    def handle_intent(self, message):
        self.speak("Here are my available I.P. addresses.")
        for ifaceName in interfaces():
            addresses = [
                i['addr'] for i in
                ifaddresses(ifaceName).setdefault(
                    AF_INET, [{'addr': None}])]
            if None in addresses:
                addresses.remove(None)
            if addresses and ifaceName != "lo":
                addresses = [re.sub(r"\.", r" dot ", address)
                             for address in addresses]
                logger.debug(addresses[0])
                self.speak('%s: %s' % (
                    "interface: " + ifaceName +
                    ", I.P. Address ", ', '.join(addresses)))
        self.speak("Those are all my I.P. addresses.")

    def stop(self):
        pass


def create_skill():
    return IPSkill()
