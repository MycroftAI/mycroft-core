# Copyright 2020 Mycroft AI Inc.
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

import abc


class MycroftSwitch:
    """abstract base class for a Mycroft Switch Array
    all switches must provide at least these basic methods"""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def terminate(self):
        """terminates any underlying threads"""
        return

    @abc.abstractmethod
    def handle_action(self):
        return

    @abc.abstractmethod
    def handle_voldown(self):
        return

    @abc.abstractmethod
    def handle_volup(self):
        return

    @abc.abstractmethod
    def handle_mute(self, val):
        return

    @abc.abstractmethod
    def get_capabilities(self):
        return
