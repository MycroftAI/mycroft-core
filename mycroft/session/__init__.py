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


import time
from threading import Lock
from uuid import uuid4

from mycroft.configuration import ConfigurationManager
from mycroft.util import log

__author__ = 'seanfitz'
logger = log.getLogger(__name__)
config = ConfigurationManager.get().get('session')


class Session(object):
    """
    An object representing a Mycroft Session Identifier
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


class SessionManager(object):
    """
    Keeps track of the current active session
    """
    __current_session = None
    __lock = Lock()

    @staticmethod
    def get():
        """
        get the active session.

        :return: An active session
        """
        with SessionManager.__lock:
            if (not SessionManager.__current_session or
                    SessionManager.__current_session.expired()):
                SessionManager.__current_session = Session(
                    str(uuid4()), expiration_seconds=config.get('ttl', 180))
                logger.info(
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
