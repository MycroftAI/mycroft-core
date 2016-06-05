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

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from random import randint
from pprint import pformat
from subprocess import check_output

__author__ = 'the7erm'

LOGGER = getLogger(__name__)


def and_(strings):
    """
    Join a list of strings with , and add 'and' at the end, because grammar
    matters.
    """
    if len(strings) <= 1:
        return " ".join(strings)

    return "%s and %s" % (", ".join(strings[0:-1]),
                          strings[-1])

# This skill is based on the welcome skill.
# The goal of this skill is to give a new developer a basic skill with
# comments, and show ways of handling input.


class HelloSkill(MycroftSkill):

    def __init__(self):
        super(HelloSkill, self).__init__(name="HelloSkill")

    def initialize(self):
        # Data file location: `mycroft/skills/hello_world/`
        self.load_data_files(dirname(__file__))

        # Read this: https://github.com/MycroftAI/adapt#intent-modelling
        hello_intent = IntentBuilder("HelloIntent")
        # Add a .voc file.
        # The .voc file is the list of words that your intent will accept
        # as input.
        # HellowKeyword tells the mycroft to use
        # `hello_world/vocab/<lang>/HelloKeyword.voc`
        hello_intent.require("HelloKeyword")
        hello_intent.build()
        """
            # You can also chain your intent.
            hello_intent = IntentBuilder("HelloIntent")\
                .require("HelloKey")\
                .build()
        """
        self.register_intent(hello_intent, self.handle_hello_intent)

    def handle_hello_intent(self, message):
        # Sometimes it's useful to log what you're doing while debugging.
        LOGGER.debug("called handle_hello_intent message.metadata:%s" %
                     message.metadata)

        # At this point most people would add
        # `self.speak_dialog('Hello')` and call it good
        # for a hello_world example, but let's have some
        # fun and mix it up.

        # List of .dialog files we'll use to say 'hi' back
        dialogs = [
            'Hello',  # `hello_world/dialog/<lang>/Hello.dialog`
            'Hi'  # `hello_world/dialog/<lang>/Hi.dialog`
        ]
        # Get a random index
        idx = randint(0, len(dialogs) - 1)
        dialog = dialogs[idx]
        self.speak_dialog(dialog)  # Say Hi, or Hello.
        LOGGER.debug("Said: '%s'" % dialog)

        how_are_yous = ("how are you doing today",
                        "how are you doing",
                        "how are you")

        # Here we check what was said by the user, and from there we
        # tell the user what the highest cpu processes are.
        if message.metadata['utterance'] in how_are_yous:
            self.speak_dialog("Fine")
            self.speak_dialog("WorkingHardOn")
            # Get the top 4 processes that are using the most CPU.
            output = check_output("ps -eo pcpu,comm --no-headers|"
                                  "sort -t. -nk1,2 -k4,4 -r |"
                                  "head -n 4 |"
                                  "awk '{print $2}'", shell=True)
            output = output.strip()
            # Replace all the "\n" with a comma then add the word
            # 'and' because grammar matters.
            LOGGER.debug("AND:%s" % and_(output.split("\n")))
            self.speak(and_(output.split("\n")))

    def stop(self):
        pass


def create_skill():
    return HelloSkill()
