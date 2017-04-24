# Copyright 2017 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

import json
import sys
from os.path import isfile


class SkillSettings(dict):
    def __init__(self, settings_file):
        super(SkillSettings, self).__init__()
        self._path = settings_file

        # if file exist, open and read stored values into self
        if isfile(self._path):
            with open(self._path) as f:
                json_data = json.load(f)
                for key in json_data:
                    self.__setitem__(key, json_data[key])

        self._is_stored = True

    def __getitem__(self, key):
        return super(SkillSettings, self).__getitem__(key)

    def __setitem__(self, key, value):
        self._is_stored = False
        return super(SkillSettings, self).__setitem__(key, value)

    def store(self):
        if not self._is_stored:
            with open(self._path, 'w')as f:
                json.dump(self, f)
