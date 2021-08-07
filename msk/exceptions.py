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
from msm import MsmException


class MskException(MsmException):
    pass


class AlreadyUpdated(MskException):
    pass


class GithubRepoExists(MskException):
    pass


class NotUploaded(MskException):
    pass


class PRModified(MskException):
    pass


class SkillNameTaken(GithubRepoExists):
    """
    raised when you try to submit a skill with an already taken unique name
    """
    pass


class UnrelatedGithubHistory(GithubRepoExists):
    """
    raised when you try to update a remote with unrelated commit history
    """
    pass


class NoGitRepository(MskException):
    """
    Raised when a skill cannot be updated because it does not belong to any
    git repo
    """
    pass

