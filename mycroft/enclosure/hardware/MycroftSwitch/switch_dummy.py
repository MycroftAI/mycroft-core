# Copyright 2022 Mycroft AI Inc.
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
from mycroft.enclosure.hardware.MycroftSwitch.MycroftSwitch import MycroftSwitch
from mycroft.util.log import LOG


class Switch(MycroftSwitch):
    """A dummy Switch control class used for testing.

    This class has been simplified from the SJ201 version for testing.

    NOTE:
    - A switch is an abstract concept which applies to buttons and switches.
    - The Mark2 actually has 4 different switches.
    - Three buttons (volume up, down and activate) and a mute mic switch.
    - All are read only and interrupt driven.
    - Switches are pulled up so the active state is actually zero.
    """

    def __init__(self, debounce=100):
        self.debounce = debounce
        self.active = 0

        # some switch implementations require a thread
        # we don't but we must meet the base requirement
        self.thread_handle = None

        self.capabilities = {
            "user_volup_handler": "button",
            "user_voldown_handler": "button",
            "user_action_handler": "button",
            "user_mute_handler": "slider",
        }

        # establish default values
        self.SW_ACTION = 1
        self.SW_VOL_UP = 1
        self.SW_VOL_DOWN = 1
        self.SW_MUTE = 1

        # establish default handlers for each switch
        self.action_handler = self.handle_action
        self.vol_up_handler = self.handle_vol_up
        self.vol_down_handler = self.handle_vol_down
        self.mute_handler = self.handle_mute

        # user overides
        self.user_voldown_handler = None
        self.user_volup_handler = None
        self.user_action_handler = None
        self.user_mute_handler = None

    def get_capabilities(self):
        return self.capabilities

    def handle_action(self, channel):
        if self.user_action_handler is not None:
            self.user_action_handler()

    def handle_vol_up(self, channel):
        if self.user_volup_handler is not None:
            self.user_volup_handler()

    def handle_vol_down(self, channel):
        if self.user_voldown_handler is not None:
            self.user_voldown_handler()

    def handle_mute(self, channel):
        # No idea why this delay is necessary, but it makes the muting reliable
        time.sleep(0.05)
        self.SW_MUTE = None

        if self.user_mute_handler is not None:
            self.user_mute_handler(self.SW_MUTE)

    def reset_xmos(self):
        """Cycle XMOS power"""
        LOG.info("switch_gpio: reset_xmos() hit")

    def terminate(self):
        LOG.info("switch_gpio: terminate hit")
