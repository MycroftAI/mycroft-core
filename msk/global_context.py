# Copyright (c) 2018 Mycroft AI, Inc.
#
# This file is part of Mycroft Skills Kit
# (see https://github.com/MycroftAI/mycroft-skills-kit).
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
from github import Github
from github.AuthenticatedUser import AuthenticatedUser
from msm import MycroftSkillsManager

from msk.lazy import Lazy, unset
from msk.util import ask_for_github_token


class GlobalContext:
    lang = Lazy(unset)  # type: str
    msm = Lazy(unset)  # type: MycroftSkillsManager
    use_token = Lazy(unset)  # type: bool
    branch = Lazy(unset)  # type: str
    github = Lazy(lambda s: ask_for_github_token())  # type: Github
    user = Lazy(lambda s: s.github.get_user())       # type: AuthenticatedUser

