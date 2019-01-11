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
#
import os
from os.path import join, expanduser, isdir


class FileSystemAccess:
    """
    A class for providing access to the mycroft FS sandbox. Intended to be
    attached to skills at initialization time to provide a skill-specific
    namespace.
    """

    def __init__(self, path):
        self.path = self.__init_path(path)

    @staticmethod
    def __init_path(path):
        if not isinstance(path, str) or len(path) == 0:
            raise ValueError("path must be initialized as a non empty string")
        path = join(expanduser('~'), '.mycroft', path)

        if not isdir(path):
            os.makedirs(path)
        return path

    def open(self, filename, mode):
        """
        Get a handle to a file (with the provided mode) within the
        skill-specific namespace.

        :param filename: a str representing a path relative to the namespace.
            subdirs not currently supported.

        :param mode: a file handle mode

        :return: an open file handle.
        """
        file_path = join(self.path, filename)
        return open(file_path, mode)

    def exists(self, filename):
        return os.path.exists(join(self.path, filename))
