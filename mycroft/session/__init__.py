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
import time
from threading import Lock
from uuid import uuid4

from mycroft.configuration import Configuration
from mycroft.util.log import LOG


class Session:
    """
    An class representing a Mycroft Session Identifier
    """

    def __init__(self, session_id, expiration_seconds=180):
        self.session_id = session_id
        self.touch_time = int(time.time())
        self.expiration_seconds = expiration_seconds

    def touch(self):
        """
        update the touch_time on the session

        :return:
        """
        self.touch_time = int(time.time())

    def expired(self):
        """
        determine if the session has expired

        :return:
        """
        return int(time.time()) - self.touch_time > self.expiration_seconds

    def __str__(self):
        return "{%s,%d}" % (str(self.session_id), self.touch_time)


class SessionManager:
    """ Keeps track of the current active session. """
    __current_session = None
    __lock = Lock()

    @staticmethod
    def get():
        """
        get the active session.

        :return: An active session
        """
        config = Configuration.get().get('session')

        with SessionManager.__lock:
            if (not SessionManager.__current_session or
                    SessionManager.__current_session.expired()):
                SessionManager.__current_session = Session(
                    str(uuid4()), expiration_seconds=config.get('ttl', 180))
                LOG.info(
                    "New Session Start: " +
                    SessionManager.__current_session.session_id)
            return SessionManager.__current_session

    @staticmethod
    def touch():
        """
        Update the last_touch timestamp on the current session

        :return: None
        """
        SessionManager.get().touch()
