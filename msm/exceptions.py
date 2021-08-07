# Copyright (c) 2018 Mycroft AI, Inc.
#
# This file is part of Mycroft Skills Manager
# (see https://github.com/MatthewScholefield/mycroft-light).
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from contextlib import contextmanager

from git import GitError


class MsmException(Exception):
    def __repr__(self):
        s = self.__str__().rstrip('\n')
        if '\n' in s:
            s = s.replace('\n', '\n\t') + '\n'
        return '{}({})'.format(self.__class__.__name__, s)


class GitException(MsmException):
    pass


class GitAuthException(GitException):
    def __repr__(self):
        return self.__class__.__name__


class MergeConflict(GitException):
    def __repr__(self):
        return self.__class__.__name__


class SkillModified(MsmException):
    """
    Raised when a skill cannot be updated because
    it has been modified by the user
    """
    pass


class RemoveException(MsmException):
    pass


class AlreadyRemoved(RemoveException):
    pass


class InstallException(MsmException):
    pass


class SkillNotFound(InstallException):
    pass


class SkillRequirementsException(InstallException):
    pass


class CloneException(InstallException):
    pass


class AlreadyInstalled(InstallException):
    pass


class NotInstalled(MsmException):
    pass


class SystemRequirementsException(InstallException):
    pass


class PipRequirementsException(InstallException):
    def __init__(self, code, stdout, stderr):
        self.code, self.stdout, self.stderr = code, stdout, stderr

    def __str__(self):
        return '\nPip returned code {}:\n{}\n{}'.format(
            self.code, self.stdout, self.stderr
        )


class MultipleSkillMatches(MsmException):
    def __init__(self, skills):
        self.skills = skills

    def __str__(self):
        return ', '.join(skill.name for skill in self.skills)


@contextmanager
def git_to_msm_exceptions():
    try:
        yield
    except GitError as e:
        msg = getattr(e, 'stderr', str(e)).replace('stderr:', '').strip()
        if 'Authentication failed for' in msg:
            raise GitAuthException(msg) from e
        if 'Not something we can merge' in msg or \
                'Not possible to fast-forward':
            raise MergeConflict(msg) from e
        raise GitException(msg) from e
