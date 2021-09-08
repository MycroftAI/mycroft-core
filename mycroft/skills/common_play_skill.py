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

import re
from enum import Enum, IntEnum
from abc import ABC, abstractmethod
from mycroft.messagebus.message import Message
from mycroft.skills.mycroft_skill import MycroftSkill
from mycroft.skills.audioservice import AudioService


class CPSMatchLevel(Enum):
    EXACT = 1
    MULTI_KEY = 2
    TITLE = 3
    ARTIST = 4
    CATEGORY = 5
    GENERIC = 6


class CPSTrackStatus(IntEnum):
    DISAMBIGUATION = 1  # not queued for playback, show in gui
    PLAYING = 20  # Skill is handling playback internally
    PLAYING_AUDIOSERVICE = 21  # Skill forwarded playback to audio service
    PLAYING_GUI = 22  # Skill forwarded playback to gui
    PLAYING_ENCLOSURE = 23  # Skill forwarded playback to enclosure
    QUEUED = 30  # Waiting playback to be handled inside skill
    QUEUED_AUDIOSERVICE = 31  # Waiting playback in audio service
    QUEUED_GUI = 32  # Waiting playback in gui
    QUEUED_ENCLOSURE = 33  # Waiting for playback in enclosure
    PAUSED = 40  # media paused but ready to resume
    STALLED = 60  # playback has stalled, reason may be unknown
    BUFFERING = 61  # media is buffering from an external source
    END_OF_MEDIA = 90  # playback finished, is the default state when CPS loads


class CommonPlaySkill(MycroftSkill, ABC):
    """ To integrate with the common play infrastructure of Mycroft
    skills should use this base class and override the two methods
    `CPS_match_query_phrase` (for checking if the skill can play the
    utterance) and `CPS_start` for launching the media.

    The class makes the skill available to queries from the
    mycroft-playback-control skill and no special vocab for starting playback
    is needed.
    """

    def __init__(self, name=None, bus=None):
        super().__init__(name, bus)
        self.audioservice = None
        self.play_service_string = None

        # "MusicServiceSkill" -> "Music Service"
        spoken = name or self.__class__.__name__
        self.spoken_name = re.sub(r"([a-z])([A-Z])", r"\g<1> \g<2>",
                                  spoken.replace("Skill", ""))
        # NOTE: Derived skills will likely want to override self.spoken_name
        # with a translatable name in their initialize() method.

    def bind(self, bus):
        """Overrides the normal bind method.

        Adds handlers for play:query and play:start messages allowing
        interaction with the playback control skill.

        This is called automatically during setup, and
        need not otherwise be used.
        """
        if bus:
            super().bind(bus)
            self.audioservice = AudioService(self.bus)
            self.add_event('play:query', self.__handle_play_query)
            self.add_event('play:start', self.__handle_play_start)

    def __handle_play_query(self, message):
        """Query skill if it can start playback from given phrase."""
        search_phrase = message.data["phrase"]
        message.context["skill_id"] = self.skill_id
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
                                            "service_name": self.spoken_name,
                                            "conf": confidence}))
        else:
            # Signal we are done (can't handle it)
            self.bus.emit(message.response({"phrase": search_phrase,
                                            "skill_id": self.skill_id,
                                            "searching": False}))

    def __calc_confidence(self, match, phrase, level):
        """Translate confidence level and match to a 0-1 value.

        "play pandora"
        "play pandora is my girlfriend"
        "play tom waits on pandora"

        Assume the more of the words that get consumed, the better the match

        Args:
            match (str): Matching string
            phrase (str): original input phrase
            level (CPSMatchLevel): match level
        """
        consumed_pct = len(match.split()) / len(phrase.split())
        if consumed_pct > 1.0:
            consumed_pct = 1.0 / consumed_pct  # deal with over/under-matching

        # We'll use this to modify the level, but don't want it to allow a
        # match to jump to the next match level.  So bonus is 0 - 0.05 (1/20)
        bonus = consumed_pct / 20.0

        if level == CPSMatchLevel.EXACT:
            return 1.0
        elif level == CPSMatchLevel.MULTI_KEY:
            return 0.9 + bonus
        elif level == CPSMatchLevel.TITLE:
            return 0.8 + bonus
        elif level == CPSMatchLevel.ARTIST:
            return 0.7 + bonus
        elif level == CPSMatchLevel.CATEGORY:
            return 0.6 + bonus
        elif level == CPSMatchLevel.GENERIC:
            return 0.5 + bonus
        else:
            return 0.0  # should never happen

    def __handle_play_start(self, message):
        """Bus handler for starting playback using the skill."""
        if message.data["skill_id"] != self.skill_id:
            # Not for this skill!
            return
        phrase = message.data["phrase"]
        data = message.data.get("callback_data")

        # Stop any currently playing audio
        if self.audioservice.is_playing:
            self.audioservice.stop()
        message.context["skill_id"] = self.skill_id
        self.bus.emit(message.forward("mycroft.stop"))

        # Save for CPS_play() later, e.g. if phrase includes modifiers like
        # "... on the chromecast"
        self.play_service_string = phrase

        self.make_active()

        # Invoke derived class to provide playback data
        self.CPS_start(phrase, data)

    def CPS_play(self, *args, **kwargs):
        """Begin playback of a media file or stream

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
        self.CPS_send_status(uri=args[0],
                             status=CPSTrackStatus.PLAYING_AUDIOSERVICE)

    def stop(self):
        """Stop anything playing on the audioservice."""
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
        """Analyze phrase to see if it is a play-able phrase with this skill.

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
        """Begin playing whatever is specified in 'phrase'

        Args:
            phrase (str): User phrase uttered after "Play", e.g. "some music"
            data (dict): Callback data specified in match_query_phrase()
        """
        # Derived classes must implement this, e.g.
        # self.CPS_play("http://zoosh.com/stream_music")
        pass

    def CPS_extend_timeout(self, timeout=5):
        """Request Common Play Framework to wait another {timeout} seconds
        for an answer from this skill.

        Args:
            timeout (int): Number of seconds
        """
        self.bus.emit(Message('play:query.response',
                              {"phrase": self.play_service_string,
                               "searching": True,
                               "timeout": timeout,
                               "skill_id": self.skill_id}))

    def CPS_send_status(self, artist='', track='', album='', image='',
                        uri='', track_length=None, elapsed_time=None,
                        playlist_position=None,
                        status=CPSTrackStatus.DISAMBIGUATION, **kwargs):
        """Inform system of playback status.

        If a skill is handling playback and wants the playback control to be
        aware of it's current status it can emit this message indicating that
        it's performing playback and can provide some standard info.

        All parameters are optional so any can be left out. Also if extra
        non-standard parameters are added, they too will be sent in the message
        data.

        Args:
            artist (str): Current track artist
            track (str): Track name
            album (str): Album title
            image (str): url for image to show
            uri (str): uri for track
            track_length (float): track length in seconds
            elapsed_time (float): current offset into track in seconds
            playlist_position (int): Position in playlist of current track
        """
        data = {'skill': self.name,
                'uri': uri,
                'artist': artist,
                'album': album,
                'track': track,
                'image': image,
                'track_length': track_length,
                'elapsed_time': elapsed_time,
                'playlist_position': playlist_position,
                'status': status
                }
        data = {**data, **kwargs}  # Merge extra arguments
        self.bus.emit(Message('play:status', data))

    def CPS_send_tracklist(self, tracklist):
        """Inform system of playlist track info.

        Provides track data for playlist

        Args:
            tracklist (list/dict): Tracklist data
        """
        tracklist = tracklist or []
        if not isinstance(tracklist, list):
            tracklist = [tracklist]
        for idx, track in enumerate(tracklist):
            self.CPS_send_status(playlist_position=idx, **track)
