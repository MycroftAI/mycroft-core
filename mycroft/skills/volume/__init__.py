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
from os.path import dirname, join

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class VolumeSkill(MycroftSkill):
    VOLUMES = {0: 0, 1: 15, 2: 25, 3: 35, 4: 45, 5: 55, 6: 65, 7: 70, 8: 80,
               9: 90, 10: 95, 11: 100}

    def __init__(self):
        super(VolumeSkill, self).__init__(name="VolumeSkill")
        self.default_volume = int(self.config.get('default_volume'))

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
        code, volume = self.get_volume(message, mixer.getvolume()[0])
        mixer.setvolume(volume)
        self.speak_dialog('set.volume', data={'volume': code})

    def handle_increase_volume(self, message):
        code, volume = self.__update_volume(1)
        self.speak_dialog('increase.volume', data={'volume': code})

    def handle_decrease_volume(self, message):
        code, volume = self.__update_volume(-1)
        self.speak_dialog('decrease.volume', data={'volume': code})

    def handle_mute_volume(self, message):
        self.speak_dialog('mute.volume')
        time.sleep(2)
        Mixer().setvolume(0)

    def handle_reset_volume(self, message):
        Mixer().setvolume(self.default_volume)
        self.speak_dialog(
            'reset.volume',
            data={'volume': self.get_volume_code(self.default_volume)})

    def __update_volume(self, level=0):
        mixer = Mixer()
        volume = mixer.getvolume()[0]
        code = self.get_volume_code(volume) + level
        code = self.fix_code(code)
        if code in self.VOLUMES:
            volume = self.VOLUMES[code]
            mixer.setvolume(volume)
        return code, volume

    def get_volume(self, message, default=None):
        amount = message.metadata.get('VolumeAmount', default)
        if not amount:
            return self.default_volume

        if amount in ['loud']:
            amount = 9
        elif amount in ['normal']:
            amount = 6
        elif amount in ['quiet']:
            amount = 3
        elif amount in ['two']:
            amount = 2
        elif amount in ['one']:
            amount = 1
        elif amount in ['zero']:
            amount = 0
        else:
            try:
                amount = int(amount)
            except:
                return self.default_volume

        amount = self.fix_code(amount)
        return amount, self.VOLUMES[amount]

    def get_volume_code(self, volume):
        for k, v in self.VOLUMES.iteritems():
            if volume <= v:
                return k

    @staticmethod
    def fix_code(code):
        if code > 11:
            code = 11
        elif code < 0:
            code = 0
        return code

    def stop(self):
        pass


def create_skill():
    return VolumeSkill()
