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

# abstract base class for a Mycroft Led
# all leds must provide at least these basic methods

class MycroftLed(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self):
        return

    @abc.abstractmethod
    def set_led(self, which_led, color, immediate):
        """set the led - if immediate is false 
           it is buffered until the next show()"""
        return
    
    @abc.abstractmethod
    def fill(self, color):
        """set all leds to the supplied color"""
        return

    @abc.abstractmethod
    def show(self):
        """update leds from buffered data"""
        return

    @abc.abstractmethod
    def get_led(self, which_led):
        """returns current buffered value"""
        return

    @abc.abstractmethod
    def set_leds(self, leds):
        """updates buffer from leds and update hardware"""
        return

    @abc.abstractmethod
    def get_capabilities(self):
        """returns capabilities object"""
        return

