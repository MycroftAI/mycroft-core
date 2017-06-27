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

"""
    This module provides the SkillSettings dictionary, which is a simple
    extension of the python dict to enable storing.

    Example:
        from mycroft.skill.settings import SkillSettings

        s = SkillSettings('./settings.json')
        s['meaning of life'] = 42
        s['flower pot sayings'] = 'Not again...'
        s.store()
"""

import json
import sys
from os.path import isfile


class SkillSettings(dict):
    """
        SkillSettings creates a dictionary that can easily be stored
        to file, serialized as json.

        Args:
            settings_file (str): Path to storage file
    """
    def __init__(self, settings_file):
        super(SkillSettings, self).__init__()
        self._path = settings_file
        # if file exist, open and read stored values into self
        if isfile(self._path):
            with open(self._path) as f:
                json_data = json.load(f)
                for key in json_data:
                    self.__setitem__(key, json_data[key])

        self.loaded_hash = hash(str(self))

    @property
    def _is_stored(self):
        return hash(str(self)) == self.loaded_hash

    def __getitem__(self, key):
        return super(SkillSettings, self).__getitem__(key)

    def __setitem__(self, key, value):
        """
            Add/Update key and note that the file needs saving.
        """
        return super(SkillSettings, self).__setitem__(key, value)

    def store(self):
        """
            Store dictionary to file if it has changed
        """
        if not self._is_stored:
            with open(self._path, 'w')as f:
                json.dump(self, f)
            self.loaded_hash = hash(str(self))
