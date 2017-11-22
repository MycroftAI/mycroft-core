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
import json
import time

from mycroft.filesystem import FileSystemAccess


class DeviceIdentity(object):
    def __init__(self, **kwargs):
        self.uuid = kwargs.get("uuid", "")
        self.access = kwargs.get("access", "")
        self.refresh = kwargs.get("refresh", "")
        self.expires_at = kwargs.get("expires_at", 0)

    def is_expired(self):
        return self.refresh and self.expires_at <= time.time()


class IdentityManager(object):
    __identity = None

    @staticmethod
    def load():
        try:
            with FileSystemAccess('identity').open('identity2.json', 'r') as f:
                IdentityManager.__identity = DeviceIdentity(**json.load(f))
        except:
            IdentityManager.__identity = DeviceIdentity()
        return IdentityManager.__identity

    @staticmethod
    def save(login=None):
        if login:
            IdentityManager.update(login)
        with FileSystemAccess('identity').open('identity2.json', 'w') as f:
            json.dump(IdentityManager.__identity.__dict__, f)

    @staticmethod
    def update(login=None):
        login = login or {}
        expiration = login.get("expiration", 0)
        IdentityManager.__identity.uuid = login.get("uuid", "")
        IdentityManager.__identity.access = login.get("accessToken", "")
        IdentityManager.__identity.refresh = login.get("refreshToken", "")
        IdentityManager.__identity.expires_at = time.time() + expiration

    @staticmethod
    def get():
        if not IdentityManager.__identity:
            IdentityManager.load()
        return IdentityManager.__identity
