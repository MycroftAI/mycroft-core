# Copyright 2021 Mycroft AI Inc.
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


class SkillControl:
    """
    the SkillControl class is used by the
    system to make skills conform to
    system level requirements.

    state - is used by the skill itself to
    manage its behavior. currently the
    system does not look at a skill's
    state (though this could change
    in the future) and there are no state
    values defined at the system level.

    states - is a dict keyed by skill state
    of intent lists. it is only used by the
    change_state() method to enable/disable
    intents based on the skill's state.

    category - the category defines the skill
    category. skill categories are used by
    the system to manage intent priority.
    for example, during converse, skills of
    category 'system' are given preference.
    old style skills do not use any of this
    and are assigned a default category of
    'undefined' during instantiation. As a
    result, currently the system only recognizes
    the 'undefined' category and the 'system'
    category. This is done intentionally
    to not restrict the use of category by
    skills for other purposes at a later date.


    default values to be overidden
    by the skill constructor in its
    constructor.
    """

    state = "inactive"
    states = None
    category = "undefined"
