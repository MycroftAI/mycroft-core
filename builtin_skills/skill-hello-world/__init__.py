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
from mycroft import MycroftSkill, intent_handler


class HelloWorldSkill(MycroftSkill):
    def __init__(self):
        """ The __init__ method is called when the Skill is first constructed.
        It is often used to declare variables or perform setup actions, however
        it cannot utilise MycroftSkill methods as the class does not yet exist.
        """
        super().__init__()
        self.learning = True
        self.log.info('[Flow Learning] in HelloWorldSkill.__init__')

    def initialize(self):
        """ Perform any final setup needed for the skill here.
        This function is invoked after the skill is fully constructed and
        registered with the system. Intents will be registered and Skill
        settings will be available."""
        # my_setting = self.settings.get('my_setting')
        self.log.info('[Flow Learning] in mycroft.skills.builtinskills.skill-hello-world.__init__.py.HelloWorldSkill.initialize, settings = ' + str(self.settings))

    # Adapt is used to match intent.
    @intent_handler(IntentBuilder('HelloWorldIntent')
                    .require('HelloWorldKeyword'))
    def handle_hello_world_intent(self, message):
        """ Skills can log useful information. These will appear in the CLI and
        the skills.log file."""
        self.log.info("There are five types of log messages: "
                      "info, debug, warning, error, and exception.")
        self.speak_dialog("hello.world", expect_response=True)

    # Adapt is used to match intent.
    @intent_handler(IntentBuilder('ThankYouIntent').require('ThankYouKeyword'))
    def handle_thank_you_intent(self, message):
        """ This is an Adapt intent handler, it is triggered by a keyword."""
        self.speak_dialog("welcome")

    # Padatious is used to match intent.
    @intent_handler('HowAreYou.intent')
    def handle_how_are_you_intent(self, message):
        """ This is a Padatious intent handler.
        It is triggered using a list of sample phrases."""
        self.speak_dialog("how.are.you")

    def stop(self):
        pass

    def converse(self, message):
        """
        The commands "结束" will immediately exit the skill.
        """
        utterances = message.data['utterances']
        if utterances:
            utterance = utterances[0]
            if "结束" in utterance or utterance == "结束":
                self.speak("您说的是" + utterance + "。本技能会话结束", expect_response=False)
                return True
            else:
                self.speak("您说的是" + utterance + "。请说下一句，若要结束，请说结束", expect_response=True)
                return True
        return False


def create_skill():
    return HelloWorldSkill()
