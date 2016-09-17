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


import time
from alsaaudio import Mixer

from adapt.intent import IntentBuilder
from os.path import dirname, join

from mycroft.skills.core import MycroftSkill
from mycroft.util import play_wav
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class VolumeSkill(MycroftSkill):
    """
    "Level" refers to the custom units from 0 to 11
    "Volume" refers to the ALSA mixer setting from 0 to 100
    """

    MIN_LEVEL = 0
    MAX_LEVEL = 11
    VOLUME_WORDS = {
        'loud': 9,
        'normal': 6,
        'quiet': 3
    }

    def __init__(self):
        super(VolumeSkill, self).__init__("VolumeSkill")
        self.default_level = self.config.get('default_level')
        self.min_volume = self.config.get('min_volume')
        self.max_volume = self.config.get('max_volume')
        self.volume_sound = join(dirname(__file__), "blop-mark-diangelo.wav")

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self.__build_set_volume()

    def __build_set_volume(self):
        intent = IntentBuilder("SetVolumeIntent").require(
            "VolumeKeyword").require("VolumeAmount").build()
        self.register_intent(intent, self.handle_set_volume)

        intent = IntentBuilder("IncreaseVolumeIntent").require(
            "IncreaseVolumeKeyword").build()
        self.register_intent(intent, self.handle_increase_volume)

        intent = IntentBuilder("DecreaseVolumeIntent").require(
            "DecreaseVolumeKeyword").build()
        self.register_intent(intent, self.handle_decrease_volume)

        intent = IntentBuilder("MuteVolumeIntent").require(
            "MuteVolumeKeyword").build()
        self.register_intent(intent, self.handle_mute_volume)

        intent = IntentBuilder("ResetVolumeIntent").require(
            "ResetVolumeKeyword").build()
        self.register_intent(intent, self.handle_reset_volume)

    def handle_set_volume(self, message):
        mixer = Mixer()
        level = self.get_volume_level(message, mixer.getvolume()[0])
        mixer.setvolume(self.level_to_volume(level))
        self.speak_dialog('set.volume', data={'volume': level})

    def communicate_volume_change(self, message, dialog, code, changed):
        play_sound = message.data.get('play_sound', False)
        if play_sound:
            if changed:
                play_wav(self.volume_sound)
        else:
            if not changed:
                dialog = 'already.max.volume'
            self.speak_dialog(dialog, data={'volume': code})

    def handle_increase_volume(self, message):
        self.communicate_volume_change(message, 'increase.volume',
                                       *self.__update_volume(+1))

    def handle_decrease_volume(self, message):
        self.communicate_volume_change(message, 'decrease.volume',
                                       *self.__update_volume(-1))

    def handle_mute_volume(self, message):
        self.speak_dialog('mute.volume')
        time.sleep(2)
        Mixer().setvolume(0)

    def handle_reset_volume(self, message):
        Mixer().setvolume(self.level_to_volume(self.default_level))
        self.speak_dialog('reset.volume', data={'volume': self.default_level})

    def volume_to_level(self, volume):
        """
        :param volume: min_volume..max_volume
        :rtype int
        """
        range = self.MAX_LEVEL - self.MIN_LEVEL
        prop = float(volume - self.min_volume) / self.max_volume
        level = int(round(self.MIN_LEVEL + range * prop))
        if level > self.MAX_LEVEL:
            level = self.MAX_LEVEL
        elif level < self.MIN_LEVEL:
            level = self.MIN_LEVEL
        return level

    def level_to_volume(self, level):
        """
        :param level: 0..MAX_LEVEL
        :rtype int
        """
        range = self.max_volume - self.min_volume
        prop = float(level) / self.MAX_LEVEL
        volume = int(round(self.min_volume + int(range) * prop))

        return volume

    @staticmethod
    def bound_level(level):
        if level > VolumeSkill.MAX_LEVEL:
            level = VolumeSkill.MAX_LEVEL
        elif level < VolumeSkill.MIN_LEVEL:
            level = VolumeSkill.MIN_LEVEL
        return level

    def __update_volume(self, change=0):
        """
        Tries to change volume level
        :param change: +1 or -1; the step to change by
        :return: new code (0..11), whether volume changed
        """
        mixer = Mixer()
        old_level = self.volume_to_level(mixer.getvolume()[0])
        new_level = self.bound_level(old_level + change)
        self.enclosure.eyes_volume(new_level)
        mixer.setvolume(self.level_to_volume(new_level))
        return new_level, new_level != old_level

    def get_volume_level(self, message, default=None):
        level_str = message.data.get('VolumeAmount', default)
        level = self.default_level

        try:
            level = self.VOLUME_WORDS[level_str]
        except KeyError:
            try:
                level = int(level_str)
            except ValueError:
                pass

        level = self.bound_level(level)
        return level

    def stop(self):
        pass


def create_skill():
    return VolumeSkill()
