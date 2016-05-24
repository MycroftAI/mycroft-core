import requests
from copy import copy
import json

MOPIDY_API = '/mopidy/rpc'

_base_dict = {'jsonrpc': '2.0', 'id': 1, 'params': {}}

class Mopidy():
    def __init__(self, url):
        self.is_playing = False
        self.url = url + MOPIDY_API
        self.volume = None
        self.clear_list(force=True)

    def find_artist(self, artist):
        d = copy(_base_dict)
        d['method'] = 'core.library.search'
        d['params'] = {'artist': [artist]}
        r = requests.post(self.url, data=json.dumps(d))
        return r.json()['result'][1]['artists']

    def get_playlists(self, filter=None):
        d = copy(_base_dict)
        d['method'] = 'core.playlists.as_list'
        r = requests.post(self.url, data=json.dumps(d))
        if filter is None:
            return r.json()['result']
        else:
            return [l for l in r.json()['result'] if filter + ':' in l['uri']]

    def find_album(self, album, filter=None):
        d = copy(_base_dict)
        d['method'] = 'core.library.search'
        d['params'] = {'album': [album]}
        r = requests.post(self.url, data=json.dumps(d))
        l = [res['albums'] for res in r.json()['result'] if 'albums' in res]
        if filter is None:
            return l
        else:
            return [i for sl in l for i in sl if filter + ':' in i['uri']]

    def find_exact(self, uris='null'):
        d = copy(_base_dict)
        d['method'] = 'core.library.find_exact'
        d['params'] = {'uris' : uris}
        r = requests.post(self.url, data=json.dumps(d))
        return r.json()

    def browse(self, uri):
        d = copy(_base_dict)
        d['method'] = 'core.library.browse'
        d['params'] = {'uri' : uri}
        r = requests.post(self.url, data=json.dumps(d))
        if 'result' in r.json():
            return r.json()['result']
        else:
            return None

    def clear_list(self, force=False):
        if self.is_playing or force:
            d = copy(_base_dict)
            d['method'] = 'core.tracklist.clear'
            r = requests.post(self.url, data=json.dumps(d))
            return r

    def add_list(self, uri):
        d = copy(_base_dict)
        d['method'] = 'core.tracklist.add'
        if type(uri) == str or type(uri) == unicode:
            d['params'] = {'uri': uri}
        elif type(uri) == list:
            d['params'] = {'uris': uri}
        else:
            return None
        r = requests.post(self.url, data=json.dumps(d))
        return r

    def play(self):
        self.is_playing = True
        d = copy(_base_dict)
        d['method'] = 'core.playback.play'
        r = requests.post(self.url, data=json.dumps(d))
        r = requests.post(self.url, data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.play"}')

    def next(self):
        if self.is_playing:
            d = copy(_base_dict)
            d['method'] = 'core.playback.next'
            r = requests.post(self.url, data=json.dumps(d))

    def previous(self):
        if self.is_playing:
            d = copy(_base_dict)
            d['method'] = 'core.playback.previous'
            r = requests.post(self.url, data=json.dumps(d))

    def stop(self):
        print self.is_playing
        if self.is_playing:
            d = copy(_base_dict)
            d['method'] = 'core.playback.stop'
            r = requests.post(self.url, data=json.dumps(d))
            self.is_playing = False

    def currently_playing(self):
        if self.is_playing:
            d = copy(_base_dict)
            d['method'] = 'core.playback.get_current_track'
            r = requests.post(self.url, data=json.dumps(d))
            return r.json()['result']
        else:
            return None
    
    def set_volume(self, percent):
        if self.is_playing:
            d = copy(_base_dict)
            d['method'] = 'core.mixer.set_volume'
            d['params'] = {'volume' : percent}
            r = requests.post(self.url, data=json.dumps(d))
        
    def lower_volume(self):
        d = copy(_base_dict)
        d['method'] = 'core.mixer.get_volume'
        r = requests.post(self.url, data=json.dumps(d))
        self.volume = r.json()['result']
        self.set_volume(20)

    def restore_volume(self):
        if self.volume is not None and self.is_playing:
            self.set_volume(self.volume) 
