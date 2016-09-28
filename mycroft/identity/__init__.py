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
        self.uuid = kwargs.get("uuid", "")
        self.access = kwargs.get("access", "")
        self.refresh = kwargs.get("refresh", "")
        self.expiration = kwargs.get("expiration", "")


class IdentityManager(object):
    __identity = None

    @staticmethod
    def load():
        try:
            with FileSystemAccess('identity').open('identity.json', 'r') as f:
                IdentityManager.__identity = DeviceIdentity(**json.load(f))
        except:
            IdentityManager.__identity = DeviceIdentity()

    @staticmethod
    def save(identity):
        IdentityManager.__identity.uuid = identity.get("uuid")
        IdentityManager.__identity.access = identity.get("accessToken")
        IdentityManager.__identity.refresh = identity.get("refreshToken")
        IdentityManager.__identity.expiration = identity.get("expiration")
        with FileSystemAccess('identity').open('identity.json', 'w') as f:
            json.dump(IdentityManager.__identity.__dict__, f)

    @staticmethod
    def get():
        if not IdentityManager.__identity:
            IdentityManager.load()
        return IdentityManager.__identity
