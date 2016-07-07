import requests
import json

from collections import OrderedDict


class Channel():
    def __init__(self, name=None, id=None, stream_url=None):
        self.name = name
        self.id = id
        self.stream_url = stream_url


CHANNEL_LIST = 'http://api.sr.se/api/v2/channels'


class SwedishRadio():
    def __init__(self):
        r = requests.get(CHANNEL_LIST, params={'format': 'json'})
        self.channels = {}
        if r:
            root = json.loads(r.text.encode('utf-8'))
            channels = root['channels']
            for c in channels:
                name = c['name'].lower()
                id = c['id']
                stream_url = c['liveaudio']['url']
                self.channels[name] = Channel(name, id, stream_url)

    def __contains__(self, channel):
        return channel in self.channels

    def get_next(current):
        keys = channels.keys()
        pos = 0
        for k in keys:
            if k == current:
                break
            pos += 1
        if pos < len(keys):
            return self.channels(keys[pos])
