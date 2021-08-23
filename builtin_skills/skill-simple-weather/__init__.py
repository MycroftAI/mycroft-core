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

from mycroft_bus_client.message import Message
from mycroft.skills.intent_services.baidu_intent_match_service import BaiduNLUService
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler
from mycroft.util.log import LOG


class SimpleWeatherSkill(MycroftSkill):
    def __init__(self):
        """ The __init__ method is called when the Skill is first constructed.
        It is often used to declare variables or perform setup actions, however
        it cannot utilise MycroftSkill methods as the class does not yet exist.
        """
        super().__init__()
        self.learning = True
        self.conversation_session_id = None
        self.baidu_skill_id = None
        self.log.info('[Flow Learning] in SimpleWeatherSkill.__init__')
        LOG.info('in __init__, self.config_core = ' + str(self.config_core))
        self.nlu_service = BaiduNLUService('4bWU5KTBkVXaCefrG8eXCCMQ', 'aYuogapjsGwHLnIfy8G9neAc2RWixwsN')

    def initialize(self):
        """ Perform any final setup needed for the skill here.
        This function is invoked after the skill is fully constructed and
        registered with the system. Intents will be registered and Skill
        settings will be available."""
        # my_setting = self.settings.get('my_setting')
        self.log.info('[Flow Learning] in mycroft.skills.builtinskills.skill-simple-weather.__init__.py.SimpleWeatherSkill.initialize, settings = ' + str(self.settings))

    @intent_handler('SimpleWeatherIntent.baidu')
    def handle_simple_weather_intent(self, message):
        LOG.info('[Flow Learning] in simple weather intent, handle_simple_weather_intent, message == ' + str(message))
        LOG.info('[Flow Learning] in simple weather intent, handle_simple_weather_intent, message.data == ' + str(message.data))
        LOG.info('[Flow Learning] in simple weather intent, handle_simple_weather_intent, message.data["session_id"] == ' + str(message.data["session_id"]))
        self.conversation_session_id = message.data["session_id"]
        self.baidu_skill_id = message.data["baidu_skill_id"]
        LOG.info('message.data["reply"]' + message.data["reply"])
        self.speak(message.data["reply"], expect_response=True)

    def stop(self):
        pass

    def converse(self, message):
        LOG.info('[Flow Learning] in SimpleWeatherSkill.converse ')
        utterances = message.data['utterances']
        if utterances:
            utterance = utterances[0]
            LOG.info('[Flow Learning] in SimpleWeatherSkill.converse, utterance , conversation_session_id = ' + str(utterance) + ',' + str(self.conversation_session_id))
            response = self.nlu_service.get_response(utterance, self.conversation_session_id, self.baidu_skill_id)
            LOG.info('[Flow Learning] in SimpleWeatherSkill.converse, response = ' + str(response))
            reply = self.nlu_service.get_reply(response, 'WEATHER')
            LOG.info('[Flow Learning] in SimpleWeatherSkill.converse, reply = ' + str(reply))
            if reply:
                if self.nlu_service.are_all_slots_satisfied(response, 'WEATHER'):
                    LOG.info('[Flow Learning] slots have been satisfied.')
                    self.speak(reply, expect_response=False)
                    self.deactive()
                    return True
                else:
                    self.speak(reply, expect_response=True)
                return True
            else:
                LOG.error('Reply is not found from the response of Baidu UNIT.')
                self.speak('抱歉，好像哪里出故障了', expect_response=False)
                return True
        return False

    def deactive(self):
        LOG.info('[Flow Learning] skill_id =' + str(self.skill_id))
        self.bus.emit(Message('deactive_skill_request',
                              {'skill_id': self.skill_id}))


def create_skill():
    return SimpleWeatherSkill()
