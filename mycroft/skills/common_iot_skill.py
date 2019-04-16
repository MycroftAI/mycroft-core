# Copyright 2019 Mycroft AI Inc.
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


# THE CLASSES IN THIS FILE ARE STILL EXPERIMENTAL, AND ARE SUBJECT TO
# CHANGES. IT IS PROVIDED NOW AS A PREVIEW, SO SKILL AUTHORS CAN GET
# AN IDEA OF WHAT IS TO COME. YOU ARE FREE TO BEGIN EXPERIMENTING, BUT
# BE WARNED THAT THE CLASSES, FUNCTIONS, ETC MAY CHANGE WITHOUT WARNING.

from abc import ABC, abstractmethod
from enum import Enum, unique
from itertools import count

from mycroft import MycroftSkill
from mycroft.messagebus.message import Message


ENTITY = "ENTITY"
SCENE = "SCENE"


_counter = count()


def auto():
    """
    Indefinitely return the next number in sequence from 0.

    This can be replaced with enum.auto when we no longer
    need to support python3.4.
    """
    return next(_counter)


class _BusKeys():
    """
    This class contains some strings used to identify
    messages on the messagebus. They are used in in
    CommonIoTSkill and the IoTController skill, but
    are not intended to be used elsewhere.
    """
    BASE = "iot"
    TRIGGER = BASE + ":trigger"
    RESPONSE = TRIGGER + ".response"
    RUN = BASE + ":run."  # Will have skill_id appened
    REGISTER = BASE + "register"
    CALL_FOR_REGISTRATION = REGISTER + ".request"


@unique
class Thing(Enum):
    """
    This class represents 'Things' which may be controlled
    by IoT Skills. This is intended to be used with the
    IoTRequest class. See that class for more details.
    """
    LIGHT = auto()
    THERMOSTAT = auto()
    DOOR = auto()
    LOCK = auto()
    PLUG = auto()
    SWITCH = auto()
    TEMPERATURE = auto()  # Control desired high and low temperatures
    HEAT = auto()  # Control desired low temperature
    AIR_CONDITIONING = auto()  # Control desired high temperature


@unique
class Attribute(Enum):
    """
    This class represents 'Attributes' of 'Things'.

    This may also grow to encompass states, e.g.
    'locked' or 'unlocked'.
    """
    BRIGHTNESS = auto()
    COLOR = auto()
    COLOR_TEMPERATURE = auto()


@unique
class Action(Enum):
    """
    This class represents 'Actions' that can be applied to
    'Things,' e.d. a LIGHT can be turned ON. It is intended
    to be used with the IoTRequest class. See that class
    for more details.
    """
    ON = auto()
    OFF = auto()
    TOGGLE = auto()
    ADJUST = auto()
    SET = auto()
    INCREASE = auto()
    DECREASE = auto()
    TRIGGER = auto()


class IoTRequest():
    """
    This class represents a request from a user to control
    an IoT device. It contains all of the information an IoT
    skill should need in order to determine if it can handle
    a user's request. The information is supplied as properties
    on the request. At present, those properties are:

    action (see the Action enum above)
    thing (see the Thing enum above)
    entity
    scene

    The 'action' is mandatory, and will always be not None. The
    other fields may be None.

    The 'entity' is intended to be used for user-defined values
    specific to a skill. For example, in a skill controlling Lights,
    an 'entity' might represent a group of lights. For a smart-lock
    skill, it might represent a specific lock, e.g. 'front door.'

    The 'scene' value is also intended to to be used for user-defined
    values. Skills that extend CommonIotSkill are expected to register
    their own scenes. The controller skill will have the ability to
    trigger multiple skills, so common scene names may trigger many
    skills, for a coherent experience.

    Skills that extend CommonIotSkill will be expected to register
    their own entities. See the documentation in CommonIotSkill for
    more details.
    """

    def __init__(self,
                 action: Action,
                 thing: Thing = None,
                 attribute: Attribute = None,
                 entity: str = None,
                 scene: str = None):

        if not thing and not entity and not scene:
            raise Exception("At least one of thing,"
                            " entity, or scene must be present!")

        self.action = action
        self.thing = thing
        self.attribute = attribute
        self.entity = entity
        self.scene = scene

    def __repr__(self):
        template = ('IoTRequest('
                    'action={action},'
                    ' thing={thing},'
                    ' attribute={attribute},'
                    ' entity={entity},'
                    ' scene={scene}'
                    ')')
        return template.format(
            action=self.action,
            thing=self.thing,
            attribute=self.attribute,
            entity='"{}"'.format(self.entity) if self.entity else None,
            scene='"{}"'.format(self.scene) if self.scene else None
        )

    def to_dict(self):
        return {
            'action': self.action.name,
            'thing': self.thing.name if self.thing else None,
            'attribute': self.attribute.name if self.attribute else None,
            'entity': self.entity,
            'scene': self.scene
        }

    @classmethod
    def from_dict(cls, data: dict):
        data = data.copy()
        data['action'] = Action[data['action']]
        if data.get('thing') not in (None, ''):
            data['thing'] = Thing[data['thing']]
        if data.get('attribute') not in (None, ''):
            data['attribute'] = Attribute[data['attribute']]

        return cls(**data)


class CommonIoTSkill(MycroftSkill, ABC):
    """
    Skills that want to work with the CommonIoT system should
    extend this class. Subclasses will be expected to implement
    two methods, `can_handle` and `run_request`. See the
    documentation for those functions for more details on how
    they are expected to behave.

    Subclasses may also register their own entities and scenes.
    See the register_entities and register_scenes methods for
    details.

    This class works in conjunction with a controller skill.
    The controller registers vocabulary and intents to capture
    IoT related requests. It then emits messages on the messagebus
    that will be picked up by all skills that extend this class.
    Each skill will have the opportunity to declare whether or not
    it can handle the given request. Skills that acknowledge that
    they are capable of handling the request will be considered
    candidates, and after a short timeout, a winner, or winners,
    will be chosen. With this setup, a user can have several IoT
    systems, and control them all without worry that skills will
    step on each other.
    """

    def bind(self, bus):
        """
        Overrides MycroftSkill.bind.

        This is called automatically during setup, and
        need not otherwise be used.

        Args:
            bus:
        """
        if bus:
            super().bind(bus)
            self.add_event(_BusKeys.TRIGGER, self._handle_trigger)
            self.add_event(_BusKeys.RUN + self.skill_id, self._run_request)
            self.add_event(_BusKeys.CALL_FOR_REGISTRATION,
                           self._handle_call_for_registration)

    def _handle_trigger(self, message: Message):
        """
        Given a message, determines if this skill can
        handle the request. If it can, it will emit
        a message on the bus indicating that.

        Args:
            message: Message
        """
        data = message.data
        request = IoTRequest.from_dict(data[IoTRequest.__name__])
        can_handle, callback_data = self.can_handle(request)
        if can_handle:
            data.update({"skill_id": self.skill_id,
                         "callback_data": callback_data})
            self.bus.emit(message.response(data))

    def _run_request(self, message: Message):
        """
        Given a message, extracts the IoTRequest and
        callback_data and sends them to the run_request
        method.

        Args:
            message: Message
        """
        request = IoTRequest.from_dict(message.data[IoTRequest.__name__])
        callback_data = message.data["callback_data"]
        self.run_request(request, callback_data)

    def _handle_call_for_registration(self, _: Message):
        """
        Register this skill's scenes and entities when requested.

        Args:
            _: Message. This is ignored.
        """
        self.register_entities_and_scenes()

    def _register_words(self, words: [str], word_type: str):
        """
        Emit a message to the controller skill to register vocab.

        Emits a message on the bus containing the type and
        the words. The message will be picked up by the
        controller skill, and the vocabulary will be registered
        to that skill.

        Args:
            words:
            word_type:
        """
        if words:
            self.bus.emit(Message(_BusKeys.REGISTER,
                                  data={"skill_id": self.skill_id,
                                        "type": word_type,
                                        "words": list(words)}))

    def register_entities_and_scenes(self):
        """
        This method will register this skill's scenes and entities.

        This should be called in the skill's `initialize` method,
        at some point after `get_entities` and `get_scenes` can
        be expected to return correct results.

        """
        self._register_words(self.get_entities(), ENTITY)
        self._register_words(self.get_scenes(), SCENE)

    def get_entities(self) -> [str]:
        """
        Get a list of custom entities.

        This is intended to be overridden by subclasses, though it
        it not required (the default implementation will return an
        empty list).

        The strings returned by this function will be registered
        as ENTITY values with the intent parser. Skills should provide
        group names, user aliases for specific devices, or anything
        else that might represent a THING or a set of THINGs, e.g.
        'bedroom', 'lamp', 'front door.' This allows commands that
        don't explicitly include a THING to still be handled, e.g.
        "bedroom off" as opposed to "bedroom lights off."
        """
        return []

    def get_scenes(self) -> [str]:
        """
        Get a list of custom scenes.

        This method is intended to be overridden by subclasses, though
        it is not required. The strings returned by this function will
        be registered as SCENE values with the intent parser. Skills
        should provide user defined scene names that they are aware of
        and capable of handling, e.g. "relax," "movie time," etc.
        """
        return []

    @abstractmethod
    def can_handle(self, request: IoTRequest):
        """
        Determine if an IoTRequest can be handled by this skill.

        This method must be implemented by all subclasses.

        An IoTRequest contains several properties (see the
        documentation for that class). This method should return
        True if and only if this skill can take the appropriate
        'action' when considering _all other properties
        of the request_. In other words, a partial match, one in which
        any piece of the IoTRequest is not known to this skill,
        and is not None, this should return (False, None).

        Args:
            request: IoTRequest

        Returns: (boolean, dict)
            True if and only if this skill knows about all the
            properties set on the IoTRequest, and a dict containing
            callback_data. If this skill is chosen to handle the
            request, this dict will be supplied to `run_request`.

            Note that the dictionary will be sent over the bus, and thus
            must be JSON serializable.
        """
        return False, None

    @abstractmethod
    def run_request(self, request: IoTRequest, callback_data: dict):
        """
        Handle an IoT Request.

        All subclasses must implement this method.

        When this skill is chosen as a winner, this function will be called.
        It will be passed an IoTRequest equivalent to the one that was
        supplied to `can_handle`, as well as the `callback_data` returned by
        `can_handle`.

        Args:
            request: IoTRequest
            callback_data: dict
        """
        pass
