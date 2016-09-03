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
import threading
import time

import requests

from mycroft.configuration import ConfigurationManager
from mycroft.session import SessionManager
from mycroft.util.log import getLogger
from mycroft.util.setup_base import get_version

LOG = getLogger("Metrics")

config = ConfigurationManager.get().get('server')


class Stopwatch(object):
    def __init__(self):
        self.timestamp = None

    def start(self):
        self.timestamp = time.time()

    def lap(self):
        cur_time = time.time()
        start_time = self.timestamp
        self.timestamp = cur_time
        return cur_time - start_time

    def stop(self):
        cur_time = time.time()
        start_time = self.timestamp
        self.timestamp = None
        return cur_time - start_time


class MetricsAggregator(object):
    """
    MetricsAggregator is not threadsafe, and multiple clients writing the
    same metric "concurrently" may result in data loss.
    """

    def __init__(self):
        self._counters = {}
        self._timers = {}
        self._levels = {}
        self._attributes = {}
        self.attr("version", get_version())

    def increment(self, name, value=1):
        cur = self._counters.get(name, 0)
        self._counters[name] = cur + value

    def timer(self, name, value):
        cur = self._timers.get(name)
        if not cur:
            self._timers[name] = []
            cur = self._timers[name] = []
        cur.append(value)

    def level(self, name, value):
        self._levels[name] = value

    def clear(self):
        self._counters = {}
        self._timers = {}
        self._levels = {}
        self._attributes = {}
        self.attr("version", get_version())

    def attr(self, name, value):
        self._attributes[name] = value

    def flush(self):
        publisher = MetricsPublisher()
        payload = {
            'counters': self._counters,
            'timers': self._timers,
            'levels': self._levels,
            'attributes': self._attributes
        }
        self.clear()
        count = (len(payload['counters']) + len(payload['timers']) +
                 len(payload['levels']))
        if count > 0:
            LOG.debug(json.dumps(payload))

            def publish():
                publisher.publish(payload)

            threading.Thread(target=publish).start()


class MetricsPublisher(object):
    def __init__(self, url=config.get("url"), enabled=config.get("metrics")):
        self.url = url
        self.enabled = enabled

    def publish(self, events):
        if 'session_id' not in events:
            session_id = SessionManager.get().session_id
            events['session_id'] = session_id
        if self.enabled:
            requests.post(
                self.url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(events), verify=False)
