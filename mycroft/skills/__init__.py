# Copyright 2017 Mycroft AI Inc.
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

""" Mycroft skills module, collection of tools for building skills.

These classes, decorators and functions are used to build skills for Mycroft.
"""


from .mycroft_skill import (MycroftSkill, intent_handler, intent_file_handler,
                            resting_screen_handler)
from .fallback_skill import FallbackSkill
from .common_iot_skill import CommonIoTSkill
from .common_play_skill import CommonPlaySkill, CPSMatchLevel
from .common_query_skill import CommonQuerySkill, CQSMatchLevel

__all__ = ['MycroftSkill',
           'intent_handler',
           'intent_file_handler',
           'resting_screen_handler',
           'FallbackSkill',
           'CommonIoTSkill',
           'CommonPlaySkill',
           'CPSMatchLevel',
           'CommonQuerySkill',
           'CQSMatchLevel']
