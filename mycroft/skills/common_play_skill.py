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

from enum import Enum
from abc import ABC, abstractmethod
from mycroft import MycroftSkill
from mycroft.skills.audioservice import AudioService
from mycroft.messagebus.message import Message


class CPSMatchLevel(Enum):
    EXACT = 1
    MULTI_KEY = 2
    TITLE = 3
    ARTIST = 4
    CATEGORY = 5
    GENERIC = 6


class CommonPlaySkill(MycroftSkill, ABC):
    def __init__(self, name=None, bus=None):
        super().__init__(name, bus)
        self.audioservice = None
        self.play_service_string = None

    def bind(self, bus):
        if bus:
            super().bind(bus)
            self.audioservice = AudioService(self.bus)
            self.add_event('play:query', self.__handle_play_query)
            self.add_event('play:start', self.__handle_play_start)

    def __handle_play_query(self, message):
        search_phrase = message.data["phrase"]

        # First, notify the requestor that we are attempting to handle
        # (this extends a timeout while this skill looks for a match)
        self.bus.emit(message.response({"phrase": search_phrase,
                                        "skill_id": self.skill_id,
                                        "searching": True}))

        # Now invoke the CPS handler to let the skill perform its search
        result = self.CPS_match_query_phrase(search_phrase)

        if result:
            match = result[0]
            level = result[1]
            callback = result[2] if len(result) > 2 else None
            confidence = self.__calc_confidence(match, search_phrase, level)
            self.bus.emit(message.response({"phrase": search_phrase,
                                            "skill_id": self.skill_id,
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

        if level == CPSMatchLevel.EXACT:
            return 1.0
        elif level == CPSMatchLevel.MULTI_KEY:
            return 0.9 + (consumed_pct / 10)
        elif level == CPSMatchLevel.TITLE:
            return 0.8 + (consumed_pct / 10)
        elif level == CPSMatchLevel.ARTIST:
            return 0.7 + (consumed_pct / 10)
        elif level == CPSMatchLevel.CATEGORY:
            return 0.6 + (consumed_pct / 10)
        elif level == CPSMatchLevel.GENERIC:
            return 0.5 + (consumed_pct / 10)
        else:
            return 0.0  # should never happen

    def __handle_play_start(self, message):
        if message.data["skill_id"] != self.skill_id:
            # Not for this skill!
            return
        phrase = message.data["phrase"]
        data = message.data.get("callback_data")

        # Stop any currently playing audio
        if self.audioservice.is_playing:
            self.audioservice.stop()
        self.bus.emit(Message("mycroft.stop"))

        # Save for CPS_play() later, e.g. if phrase includes modifiers like
        # "... on the chromecast"
        self.play_service_string = phrase

        # Invoke derived class to provide playback data
        self.CPS_start(phrase, data)

    def CPS_play(self, *args, **kwargs):
        """
        Begin playback of a media file or stream

        Normally this method will be invoked with somthing like:
           self.CPS_play(url)
        Advanced use can also include keyword arguments, such as:
           self.CPS_play(url, repeat=True)

        Args:
            same as the Audioservice.play method
        """
        # Inject the user's utterance in case the audio backend wants to
        # interpret it.  E.g. "play some rock at full volume on the stereo"
        if 'utterance' not in kwargs:
            kwargs['utterance'] = self.play_service_string
        self.audioservice.play(*args, **kwargs)

    def stop(self):
        if self.audioservice.is_playing:
            self.audioservice.stop()
            return True
        else:
            return False

    ######################################################################
    # Abstract methods
    # All of the following must be implemented by a skill that wants to
    # act as a CommonPlay Skill
    @abstractmethod
    def CPS_match_query_phrase(self, phrase):
        """
        Analyze phrase to see if it is a play-able phrase with this
        skill.

        Args:
            phrase (str): User phrase uttered after "Play", e.g. "some music"

        Returns:
            (match, CPSMatchLevel[, callback_data]) or None: Tuple containing
                 a string with the appropriate matching phrase, the PlayMatch
                 type, and optionally data to return in the callback if the
                 match is selected.
        """
        # Derived classes must implement this, e.g.
        #
        # if phrase in ["Zoosh"]:
        #     return ("Zoosh", CPSMatchLevel.Generic, {"hint": "music"})
        # or:
        # zoosh_song = find_zoosh(phrase)
        # if zoosh_song and "Zoosh" in phrase:
        #     # "play Happy Birthday in Zoosh"
        #     return ("Zoosh", CPSMatchLevel.MULTI_KEY, {"song": zoosh_song})
        # elif zoosh_song:
        #     # "play Happy Birthday"
        #     return ("Zoosh", CPSMatchLevel.TITLE, {"song": zoosh_song})
        # elif "Zoosh" in phrase
        #     # "play Zoosh"
        #     return ("Zoosh", CPSMatchLevel.GENERIC, {"cmd": "random"})
        return None

    @abstractmethod
    def CPS_start(self, phrase, data):
        """
        Begin playing whatever is specified in 'phrase'

        Args:
            phrase (str): User phrase uttered after "Play", e.g. "some music"
            data (dict): Callback data specified in match_query_phrase()
        """
        # Derived classes must implement this, e.g.
        # self.CPS_play("http://zoosh.com/stream_music")
        pass
