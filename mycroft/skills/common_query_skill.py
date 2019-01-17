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

from enum import IntEnum
from abc import ABC, abstractmethod
from mycroft import MycroftSkill
from mycroft.messagebus.message import Message
from multiprocessing.pool import ThreadPool


class CQSMatchLevel(IntEnum):
    EXACT = 1  # Skill could find a specific answer for the question
    CATEGORY = 2  # Skill could find an answer from a category in the query
    GENERAL = 3  # The query could be processed as a general quer


# Copy of CQSMatchLevel to use if the skill returns visual media
CQSVisualMatchLevel = IntEnum('CQSVisualMatchLevel',
                              [e.name for e in CQSMatchLevel])


def is_CQSVisualMatchLevel(match_level):
    return isinstance(match_level, type(CQSVisualMatchLevel.EXACT))


VISUAL_DEVICES = ['mycroft_mark_2']


def handles_visuals(self, platform):
    return platform in VISUAL_DEVICES


class CommonQuerySkill(MycroftSkill, ABC):
    pool = ThreadPool(5)

    def __init__(self, name=None, bus=None):
        super().__init__(name, bus)

    def bind(self, bus):
        if bus:
            super().bind(bus)
            self.add_event('question:query', self.__handle_question_query)
            self.add_event('question:action', self.__handle_query_action)

    def __handle_question_query(self, message):
        CommonQuerySkill.pool.apply_async(self.__thread_question_query,
                                          args=[message])

    def __thread_question_query(self, message):
        search_phrase = message.data["phrase"]

        # First, notify the requestor that we are attempting to handle
        # (this extends a timeout while this skill looks for a match)
        self.bus.emit(message.response({"phrase": search_phrase,
                                        "skill_id": self.skill_id,
                                        "searching": True}))

        # Now invoke the CQS handler to let the skill perform its search
        result = self.CQS_match_query_phrase(search_phrase)

        if result:
            match = result[0]
            level = result[1]
            answer = result[2]
            callback = result[3] if len(result) > 3 else None
            confidence = self.__calc_confidence(match, search_phrase, level)
            self.bus.emit(message.response({"phrase": search_phrase,
                                            "skill_id": self.skill_id,
                                            "answer": answer,
                                            "callback_data": callback,
                                            "conf": confidence}))
        else:
            # Signal we are done (can't handle it)
            self.bus.emit(message.response({"phrase": search_phrase,
                                            "skill_id": self.skill_id,
                                            "searching": False}))

    def __calc_confidence(self, match, phrase, level):
        # Assume the more of the words that get consumed, the better the match
        consumed_pct = len(match.split()) / len(phrase.split())
        if consumed_pct > 1.0:
            consumed_pct = 1.0

        # Add bonus if match has visuals and the device supports them.
        platform = self.config_core.get('encolsure', {}).get('platform')
        if is_CQSVisualMatchLevel(level) and handles_visuals(platform):
            bonus = 0.1
        else:
            bonus = 0

        if int(level) == int(CQSMatchLevel.EXACT):
            return 0.9 + (consumed_pct / 10) + bonus
        elif int(level) == int(CQSMatchLevel.CATEGORY):
            return 0.6 + (consumed_pct / 10) + bonus
        elif int(level) == int(CQSMatchLevel.GENERAL):
            return 0.5 + (consumed_pct / 10) + bonus
        else:
            return 0.0  # should never happen

    def __handle_query_action(self, message):
        """ Message handler for question:action. Extracts phrase and data from
            message forward this to the skills CQS_action method. """
        if message.data["skill_id"] != self.skill_id:
            # Not for this skill!
            return
        phrase = message.data["phrase"]
        data = message.data.get("callback_data")
        # Invoke derived class to provide playback data
        self.CQS_action(phrase, data)

    @abstractmethod
    def CQS_match_query_phrase(self, phrase):
        """
        Analyze phrase to see if it is a play-able phrase with this
        skill. Needs to be implemented by the skill.

        Args:
            phrase (str): User phrase uttered after "Play", e.g. "some music"

        Returns:
            (match, CQSMatchLevel[, callback_data]) or None: Tuple containing
                 a string with the appropriate matching phrase, the PlayMatch
                 type, and optionally data to return in the callback if the
                 match is selected.
        """
        # Derived classes must implement this, e.g.
        return None

    def CQS_action(self, phrase, data):
        """
        Take additional action IF the skill is selected.
        The speech is handled by the common query but if the chosen skill
        wants to display media, set a context or prepare for sending
        information info over e-mail this can be implemented here.

        Args:
            phrase (str): User phrase uttered after "Play", e.g. "some music"
            data (dict): Callback data specified in match_query_phrase()
        """
        # Derived classes may implement this if they use additional media
        # or wish to set context after being called.
        pass
