# Copyright 2019 Mycroft AI Inc.
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
#
from mycroft.skills.mycroft_skill.mycroft_skill import MycroftSkill
from mycroft.skills.mycroft_skill.event_container import get_handler_name
from mycroft.skills.mycroft_skill.decorators import (intent_handler,
                                                     intent_file_handler,
                                                     resting_screen_handler,
                                                     skill_api_method)
