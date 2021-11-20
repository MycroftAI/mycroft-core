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
import time

from enum import IntEnum
from abc import ABC, abstractmethod
from mycroft.skills.mycroft_skill import MycroftSkill

from mycroft.configuration import Configuration
from mycroft.util.file_utils import resolve_resource_file


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

"""these are for the confidence calculation"""
# how much each topic word is worth
# when found in the answer
TOPIC_MATCH_RELEVANCE = 5

# elevate relevance above all else
RELEVANCE_MULTIPLIER = 2

# we like longer articles but only so much
MAX_ANSWER_LEN_FOR_CONFIDENCE = 50

# higher number - less bias for word length
WORD_COUNT_DIVISOR = 100


def handles_visuals(platform):
    return platform in VISUAL_DEVICES


class CommonQuerySkill(MycroftSkill, ABC):
    """Question answering skills should be based on this class.

    The skill author needs to implement `CQS_match_query_phrase` returning an
    answer and can optionally implement `CQS_action` to perform additional
    actions if the skill's answer is selected.

    This class works in conjunction with skill-query which collects
    answers from several skills presenting the best one available.
    """

    def __init__(self, name=None, bus=None):
        super().__init__(name, bus)
        noise_words_filepath = "text/%s/noise_words.list" % (self.lang,)
        noise_words_filename = resolve_resource_file(noise_words_filepath)
        self.translated_noise_words = []
        try:
            with open(noise_words_filename) as f:
                self.translated_noise_words = f.read().strip()
            self.translated_noise_words = self.translated_noise_words.split()
        except FileNotFoundError:
            self.log.warning("Missing noise_words.list file in res/text/lang")

        # these should probably be configurable
        self.level_confidence = {
            CQSMatchLevel.EXACT: 0.9,
            CQSMatchLevel.CATEGORY: 0.6,
            CQSMatchLevel.GENERAL: 0.5
        }

    def bind(self, bus):
        """Overrides the default bind method of MycroftSkill.

        This registers messagebus handlers for the skill during startup
        but is nothing the skill author needs to consider.
        """
        if bus:
            super().bind(bus)
            self.add_event('question:query', self.__handle_question_query)
            self.add_event('question:action', self.__handle_query_action)

    def __handle_question_query(self, message):
        search_phrase = message.data["phrase"]
        message.context["skill_id"] = self.skill_id
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
            confidence = self.__calc_confidence(
                match, search_phrase, level, answer)
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

    def remove_noise(self, phrase):
        """remove noise to produce essence of question"""
        phrase = ' ' + phrase + ' '
        for word in self.translated_noise_words:
            mtch = ' ' + word + ' '
            if phrase.find(mtch) > -1:
                phrase = phrase.replace(mtch, " ")
        phrase = ' '.join(phrase.split())
        return phrase.strip()

    def __calc_confidence(self, match, phrase, level, answer):
        # Assume the more of the words that get consumed, the better the match
        consumed_pct = len(match.split()) / len(phrase.split())
        if consumed_pct > 1.0:
            consumed_pct = 1.0
        consumed_pct /= 10

        # bonus for more sentences
        num_sentences = float(float(len(answer.split("."))) / float(10))

        # Add bonus if match has visuals and the device supports them.
        platform = self.config_core.get("enclosure", {}).get("platform")
        bonus = 0.0
        if is_CQSVisualMatchLevel(level) and handles_visuals(platform):
            bonus = 0.1

        # extract topic
        topic = self.remove_noise(match)

        # calculate relevance
        answer = answer.lower()
        matches = 0
        for word in topic.split(' '):
            if answer.find(word) > -1:
                matches += TOPIC_MATCH_RELEVANCE

        answer_size = len(answer.split(" "))
        answer_size = min(MAX_ANSWER_LEN_FOR_CONFIDENCE, answer_size)

        relevance = 0.0
        if answer_size > 0:
            relevance = float(float(matches) / float(answer_size))

        relevance = relevance * RELEVANCE_MULTIPLIER

        # extra credit for more words up to a point
        wc_mod = float(float(answer_size) / float(WORD_COUNT_DIVISOR)) * 2

        confidence = self.level_confidence[level] + \
                     consumed_pct + bonus + num_sentences + relevance + wc_mod

        return confidence

    def __handle_query_action(self, message):
        """Message handler for question:action.

        Extracts phrase and data from message forward this to the skills
        CQS_action method.
        """
        if message.data["skill_id"] != self.skill_id:
            # Not for this skill!
            return
        phrase = message.data["phrase"]
        data = message.data.get("callback_data")
        # Invoke derived class to provide playback data
        self.CQS_action(phrase, data)

    @abstractmethod
    def CQS_match_query_phrase(self, phrase):
        """Analyze phrase to see if it is a play-able phrase with this skill.

        Needs to be implemented by the skill.

        Args:
            phrase (str): User phrase, "What is an aardwark"

        Returns:
            (match, CQSMatchLevel[, callback_data]) or None: Tuple containing
                 a string with the appropriate matching phrase, the PlayMatch
                 type, and optionally data to return in the callback if the
                 match is selected.
        """
        # Derived classes must implement this, e.g.
        return None

    def CQS_action(self, phrase, data):
        """Take additional action IF the skill is selected.

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
