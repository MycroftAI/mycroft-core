# Copyright 2016 Mycroft AI, Inc.
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

from mycroft.filesystem import FileSystemAccess


class DeviceIdentity(object):
    def __init__(self, **kwargs):
        self.uuid = kwargs.get('uuid', "")
        self.token = kwargs.get('token', "")


class IdentityManager(object):
    FILE = 'identity.json'

    def __init__(self):
        self.file_system = FileSystemAccess('identity')
        self.identity = DeviceIdentity()
        self.load()

    def load(self):
        with self.file_system.open(self.FILE, 'r') as f:
            self.identity = DeviceIdentity(**json.load(f))

    def save(self, identity):
        self.identity = identity
        with self.file_system.open(self.FILE, 'w') as f:
            json.dump(self.identity, f)

    def get(self):
        return self.identity
