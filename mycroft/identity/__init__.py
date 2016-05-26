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


from uuid import uuid4
import json
from mycroft.filesystem import FileSystemAccess


class DeviceIdentity(object):
    def __init__(self, **kwargs):
        self.device_id = kwargs.get('device_id')
        self.owner = kwargs.get('owner')
        self.token = kwargs.get('token')

    @staticmethod
    def load(identity_file_handle):
        json_blob = json.load(identity_file_handle)
        return DeviceIdentity(**json_blob)

    def save(self, identity_file_handle):
        json.dump(self.__dict__, identity_file_handle)


class IdentityManager(object):
    def __init__(self):
        self.filesystem = FileSystemAccess('identity')
        self.identity = None
        self.initialize()

    def initialize(self):
        if self.filesystem.exists('identity.json'):
            self.identity = DeviceIdentity.load(self.filesystem.open(
                'identity.json', 'r'))
        else:
            identity = DeviceIdentity(device_id=str(uuid4()))
            self.update(identity)

    def update(self, identity):
        self.identity = identity
        with self.filesystem.open('identity.json', 'w') as f:
            self.identity.save(f)

    def is_paired(self):
        return self.identity is not None and self.identity.owner is not None

    def get(self):
        return self.identity
