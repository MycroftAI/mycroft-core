import json
import threading
import time
import requests

from mycroft.util import str2bool
from mycroft.util.log import getLogger
from mycroft.configuration.config import ConfigurationManager
from mycroft.session import SessionManager
from mycroft.util.setup_base import get_version

config = ConfigurationManager.get_config().get('metrics_client')
metrics_log = getLogger("METRICS")

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
        count = len(payload['counters']) + len(payload['timers']) + len(payload['levels'])
        if count > 0:
            metrics_log.debug(json.dumps(payload))
            def publish():
                publisher.publish(payload)
            threading.Thread(target=publish).start()


class MetricsPublisher(object):
    def __init__(self,
                 url=config.get("url"),
                 enabled=str2bool(config.get("enabled"))):
        self.url = url
        self.enabled = enabled

    def publish(self, events):
        if 'session_id' not in events:
            session_id = SessionManager.get().session_id
            events['session_id'] = session_id
        if self.enabled:
            requests.post(self.url, headers={'Content-Type': 'application/json'}, data=json.dumps(events), verify=False)
