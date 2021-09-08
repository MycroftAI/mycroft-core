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
from contextlib import contextmanager
from enum import Enum, unique
from functools import total_ordering, wraps
from itertools import count

from mycroft.skills.mycroft_skill import MycroftSkill
from mycroft.messagebus.message import Message, dig_for_message

ENTITY = "ENTITY"
SCENE = "SCENE"
IOT_REQUEST_ID = "iot_request_id"  # TODO make the id a property of the request

_counter = count()


def auto():
    """
    Indefinitely return the next number in sequence from 0.

    This can be replaced with enum.auto when we no longer
    need to support python3.4.
    """
    return next(_counter)


class _BusKeys:
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
    SPEAK = BASE + ":speak"


####################################################################
# When adding a new Thing, Attribute, etc, be sure to also add the #
# corresponding voc files to the skill-iot-control.                #
####################################################################

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
    """
    BRIGHTNESS = auto()
    COLOR = auto()
    COLOR_TEMPERATURE = auto()
    TEMPERATURE = auto()


@unique
class State(Enum):
    """
    This class represents 'States' of 'Things'.

    These are generally intended to handle binary
    queries, such as "is the door locked?" or
    "is the heat on?" where 'locked' and 'on'
    are the state values. The special value
    'STATE' can be used for more general queries
    capable of providing more detailed in formation,
    for example, "what is the state of the lamp?"
    could produce state information that includes
    brightness or color.
    """
    STATE = auto()
    POWERED = auto()
    UNPOWERED = auto()
    LOCKED = auto()
    UNLOCKED = auto()
    OCCUPIED = auto()
    UNOCCUPIED = auto()


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
    BINARY_QUERY = auto()  # yes/no answer
    INFORMATION_QUERY = auto()  # detailed answer
    LOCATE = auto()
    LOCK = auto()
    UNLOCK = auto()


@total_ordering
class IoTRequestVersion(Enum):
    """
    Enum indicating support IoTRequest fields

    This class allows us to extend the request without
    requiring that all existing skills are updated to
    handle the new fields. Skills will simply not respond
    to requests that contain fields they are not aware of.

    CommonIoTSkill subclasses should override
    CommonIoTSkill.supported_request_version to indicate
    their level of support. For backward compatibility,
    the default is V1.

    Note that this is an attempt to avoid false positive
    matches (i.e. prevent skills from reporting that they
    can handle a request that contains fields they don't
    know anything about). To avoid any possibility of
    false negatives, however, skills should always try to
    support the latest version.

    Version to supported fields (provided only for reference - always use the
    latest version available, and account for all fields):

    V1 = {'action', 'thing', 'attribute', 'entity', 'scene'}
    V2 = V1 | {'value'}
    V3 = V2 | {'state'}
    """

    def __lt__(self, other):
        return self.name < other.name

    V1 = {'action', 'thing', 'attribute', 'entity', 'scene'}
    V2 = V1 | {'value'}
    V3 = V2 | {'state'}


class IoTRequest:
    """
    This class represents a request from a user to control
    an IoT device. It contains all of the information an IoT
    skill should need in order to determine if it can handle
    a user's request. The information is supplied as properties
    on the request. At present, those properties are:

    action (see the Action enum)
    thing (see the Thing enum)
    state (see the State enum)
    attribute (see the Attribute enum)
    value
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

    The 'value' property will be a number value. This is intended to
    be used for requests such as "set the heat to 70 degrees" and
    "set the lights to 50% brightness."

    Skills that extend CommonIotSkill will be expected to register
    their own entities. See the documentation in CommonIotSkill for
    more details.
    """

    def __init__(self,
                 action: Action,
                 thing: Thing = None,
                 attribute: Attribute = None,
                 entity: str = None,
                 scene: str = None,
                 value: int = None,
                 state: State = None):

        if not thing and not entity and not scene:
            raise Exception("At least one of thing,"
                            " entity, or scene must be present!")

        self.action = action
        self.thing = thing
        self.attribute = attribute
        self.entity = entity
        self.scene = scene
        self.value = value
        self.state = state

    def __repr__(self):
        template = ('IoTRequest('
                    'action={action},'
                    ' thing={thing},'
                    ' attribute={attribute},'
                    ' entity={entity},'
                    ' scene={scene},'
                    ' value={value},'
                    ' state={state}'
                    ')')
        entity = '"{}"'.format(self.entity) if self.entity else None
        scene = '"{}"'.format(self.scene) if self.scene else None
        value = '"{}"'.format(self.value) if self.value is not None else None
        return template.format(
            action=self.action,
            thing=self.thing,
            attribute=self.attribute,
            entity=entity,
            scene=scene,
            value=value,
            state=self.state
        )

    @property
    def version(self):
        if self.state is not None:
            return IoTRequestVersion.V3
        if self.value is not None:
            return IoTRequestVersion.V2
        return IoTRequestVersion.V1

    def to_dict(self):
        return {
            'action': self.action.name,
            'thing': self.thing.name if self.thing else None,
            'attribute': self.attribute.name if self.attribute else None,
            'entity': self.entity,
            'scene': self.scene,
            'value': self.value,
            'state': self.state.name if self.state else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        data = data.copy()
        data['action'] = Action[data['action']]
        if data.get('thing') not in (None, ''):
            data['thing'] = Thing[data['thing']]
        if data.get('attribute') not in (None, ''):
            data['attribute'] = Attribute[data['attribute']]
        if data.get('state') not in (None, ''):
            data['state'] = State[data['state']]

        return cls(**data)


def _track_request(func):
    """
    Used within the CommonIoT skill to track IoT requests.

    The primary purpose of tracking the reqeust is determining
    if the skill is currently handling an IoT request, or is
    running a standard intent. While running IoT requests, certain
    methods defined on MycroftSkill should behave differently than
    under normal circumstances. In particular, speech related methods
    should not actually trigger speech, but instead pass the message
    to the IoT control skill, which will handle deconfliction (in the
    event multiple skills want to respond verbally to the same request).

    Args:
        func: Callable

    Returns:
        Callable

    """

    @wraps(func)
    def tracking_function(self, message: Message):
        with self._current_request(message.data.get(IOT_REQUEST_ID)):
            func(self, message)

    return tracking_function


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

    @wraps(MycroftSkill.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_iot_request = None

    def bind(self, bus):
        """
        Overrides MycroftSkill.bind.

        This is called automatically during setup, and
        need not otherwise be used.

        Subclasses that override this method must call this
        via super in their implementation.

        Args:
            bus:
        """
        if bus:
            super().bind(bus)
            self.add_event(_BusKeys.TRIGGER, self._handle_trigger)
            self.add_event(_BusKeys.RUN + self.skill_id, self._run_request)
            self.add_event(_BusKeys.CALL_FOR_REGISTRATION,
                           self._handle_call_for_registration)

    @contextmanager
    def _current_request(self, id: str):
        # Multiple simultaneous requests may interfere with each other as they
        # would overwrite this value, however, this seems unlikely to cause
        # any real world issues and tracking multiple requests seems as
        # likely to cause issues as to solve them.
        self._current_iot_request = id
        yield id
        self._current_iot_request = None

    @_track_request
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

        if request.version > self.supported_request_version:
            return

        can_handle, callback_data = self.can_handle(request)
        if can_handle:
            data.update({"skill_id": self.skill_id,
                         "callback_data": callback_data})
            message.context["skill_id"] = self.skill_id
            self.bus.emit(message.response(data))

    @_track_request
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

    def speak(self, utterance, *args, **kwargs):
        if self._current_iot_request:
            message = dig_for_message()
            message.context["skill_id"] = self.skill_id
            self.bus.emit(message.forward(_BusKeys.SPEAK,
                                          data={"skill_id": self.skill_id,
                                                IOT_REQUEST_ID:
                                                    self._current_iot_request,
                                                "speak_args": args,
                                                "speak_kwargs": kwargs,
                                                "speak": utterance}))
        else:
            super().speak(utterance, *args, **kwargs)

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
                                        "words": list(words)},
                                  context={"skill_id": self.skill_id}))

    def register_entities_and_scenes(self):
        """
        This method will register this skill's scenes and entities.

        This should be called in the skill's `initialize` method,
        at some point after `get_entities` and `get_scenes` can
        be expected to return correct results.

        """
        self._register_words(self.get_entities(), ENTITY)
        self._register_words(self.get_scenes(), SCENE)

    @property
    def supported_request_version(self) -> IoTRequestVersion:
        """
        Get the supported IoTRequestVersion

        By default, this returns IoTRequestVersion.V1. Subclasses
        should override this to indicate higher levels of support.

        The documentation for IoTRequestVersion provides a reference
        indicating which fields are included in each version. Note
        that you should always take the latest, and account for all
        request fields.
        """
        return IoTRequestVersion.V1

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
        'action' when considering all other properties
        of the request. In other words, a partial match, one in which
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
