# Copyright 2018 Mycroft AI Inc.
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

from abc import ABC, abstractmethod
from enum import Enum
from mycroft import MycroftSkill
from mycroft.messagebus.message import Message

class BusKeys():
    BASE = "iot"
    TRIGGER = BASE + ":trigger"
    RESPONSE = TRIGGER + ".response"
    RUN = BASE + ":run."  # Will have skill_id appened


class Thing(Enum):
    LIGHT = 0
    THERMOSTAT = 1
    DOOR = 2
    LOCK = 3
    PLUG = 4
    SWITCH = 5


class Action(Enum):
    ON = 0
    OFF = 1
    TOGGLE = 2


class IoTRequest():

    def __init__(self,
                 action: Action,
                 thing: Thing = None,
                 entity: str=None,
                 scene: str=None):

        if (not thing and not entity and not scene):
            raise Exception("At least one of thing,"
                            " entity, or scene must be present!")

        self.thing = thing
        self.action = action
        self.entity = entity
        self.scene = scene

    def __repr__(self):
        template = "IoTRequest(thing={thing}, action={action}," \
                   " entity={entity}, scene={scene})"
        return template.format(
            thing=self.thing,
            action=self.action,
            entity=self.entity,
            scene=self.scene
        )


class CommonIoTSkill(MycroftSkill, ABC):
    def __init__(self, name=None, bus=None):
        super().__init__(name, bus)

    def bind(self, bus):
        if bus:
            super().bind(bus)
            self.add_event(BusKeys.TRIGGER, self._handle_trigger)
            self.add_event(BusKeys.RUN + self.skill_id, self.run_request)

    def _handle_trigger(self, message: Message):
        data = message.data
        request = eval(data[IoTRequest.__name__])
        can_handle, callback_data = self.can_handle(request)
        if can_handle:
            data.update({"skill_id": self.skill_id,
                         "callback_data": callback_data})
            self.bus.emit(message.response(data))


    ######################################################################
    # Abstract methods
    # All of the following must be implemented by a skill that wants to
    # act as a CommonPlay Skill
    @abstractmethod
    def can_handle(self, request: IoTRequest):
        return False, None

    @abstractmethod
    def run_request(self, message: Message):
        pass
