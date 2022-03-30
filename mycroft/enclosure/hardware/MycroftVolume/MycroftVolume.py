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


class MycroftVolume:
    """abstract base class for a Mycroft Volume
    all volume classes must provide at least
    these basic methods"""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def set_hw_volume(self, vol):
        """takes in value between 0.0 - 1.0
        converts to internal format"""
        return

    @abc.abstractmethod
    def get_hw_volume(self):
        """returns float from internal format"""

    @abc.abstractmethod
    def get_capabilities(self):
        """returns capabilities object"""
        return
