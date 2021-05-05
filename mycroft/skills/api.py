# Copyright 2020 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Skill Api

The skill api allows skills interact with eachother over the message bus
just like interacting with any other object.
"""
from mycroft.messagebus.message import Message


class SkillApi():
    """SkillApi providing a simple interface to exported methods from skills

    Methods are built from a method_dict provided when initializing the skill.
    """
    bus = None

    @classmethod
    def connect_bus(cls, mycroft_bus):
        """Registers the bus object to use."""
        cls.bus = mycroft_bus

    def __init__(self, method_dict):
        self.method_dict = method_dict
        for key in method_dict:
            def get_method(k):
                def method(*args, **kwargs):
                    m = self.method_dict[k]
                    data = {'args': args, 'kwargs': kwargs}
                    method_msg = Message(m['type'], data)
                    response = SkillApi.bus.wait_for_response(method_msg)
                    if (response and response.data and
                            'result' in response.data):
                        return response.data['result']
                    else:
                        return None

                return method

            self.__setattr__(key, get_method(key))

    @staticmethod
    def get(skill):
        """Generate api object from skill id.
        Args:
            skill (str): skill id for target skill

        Returns:
            SkillApi
        """
        public_api_msg = '{}.public_api'.format(skill)
        api = SkillApi.bus.wait_for_response(Message(public_api_msg))
        if api:
            return SkillApi(api.data)
        else:
            return None
