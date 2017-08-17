import requests
from copy import copy
import json

MOPIDY_API = '/mopidy/rpc'

_base_dict = {'jsonrpc': '2.0', 'id': 1, 'params': {}}


class Mopidy(object):
    def __init__(self, url):
        print "MOPIDY URL: " + url
        self.is_playing = False
        self.url = url + MOPIDY_API
        self.volume = None
        self.clear_list(force=True)
        self.volume_low = 3
        self.volume_high = 100

    def find_artist(self, artist):
        d = copy(_base_dict)
        d['method'] = 'core.library.search'
        d['params'] = {'artist': [artist]}
        r = requests.post(self.url, data=json.dumps(d))
        return r.json()['result'][1]['artists']

    def get_playlists(self, filter=None):
        print "GETTING PLAYLISTS"
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
        d['params'] = {'uris': uris}
        r = requests.post(self.url, data=json.dumps(d))
        return r.json()

    def browse(self, uri):
        d = copy(_base_dict)
        d['method'] = 'core.library.browse'
        d['params'] = {'uri': uri}
        print "BROWSE"
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
        self.restore_volume()
        d = copy(_base_dict)
        d['method'] = 'core.playback.play'
        r = requests.post(self.url, data=json.dumps(d))

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
            d['params'] = {'volume': percent}
            r = requests.post(self.url, data=json.dumps(d))

    def lower_volume(self):
        self.set_volume(self.volume_low)

    def restore_volume(self):
        self.set_volume(self.volume_high)

    def pause(self):
        if self.is_playing:
            d = copy(_base_dict)
            d['method'] = 'core.playback.pause'
            r = requests.post(self.url, data=json.dumps(d))

    def resume(self):
        if self.is_playing:
            d = copy(_base_dict)
            d['method'] = 'core.playback.resume'
            r = requests.post(self.url, data=json.dumps(d))

    def get_items(self, uri):
        d = copy(_base_dict)
        d['method'] = 'core.playlists.get_items'
        d['params'] = {'uri': uri}
        r = requests.post(self.url, data=json.dumps(d))
        if 'result' in r.json():
            print r.json()
            return [e['uri'] for e in r.json()['result']]
        else:
            return None

    def get_tracks(self, uri):
        tracks = self.browse(uri)
        ret = [t['uri'] for t in tracks if t['type'] == 'track']

        sub_tracks = [t['uri'] for t in tracks if t['type'] != 'track']
        for t in sub_tracks:
            ret = ret + self.get_tracks(t)
        return ret

    def get_local_albums(self):
        p = self.browse('local:directory?type=album')
        return {e['name']: e for e in p if e['type'] == 'album'}

    def get_local_artists(self):
        p = self.browse('local:directory?type=artist')
        return {e['name']: e for e in p if e['type'] == 'artist'}

    def get_local_genres(self):
        p = self.browse('local:directory?type=genre')
        return {e['name']: e for e in p if e['type'] == 'directory'}

    def get_local_playlists(self):
        print "GETTING PLAYLISTS"
        p = self.get_playlists('m3u')
        print "RETURNING PLAYLISTS"
        return {e['name']: e for e in p}

    def get_spotify_playlists(self):
        p = self.get_playlists('spotify')
        return {e['name'].split('(by')[0].strip().lower(): e for e in p}

    def get_gmusic_albums(self):
        p = self.browse('gmusic:album')
        print p
        p = {e['name']: e for e in p if e['type'] == 'directory'}
        print p
        return {e.split(' - ')[1]: p[e] for e in p}

    def get_gmusic_artists(self):
        p = self.browse('gmusic:artist')
        return {e['name']: e for e in p if e['type'] == 'directory'}

    def get_gmusic_radio(self):
        p = self.browse('gmusic:radio')
        return {e['name']: e for e in p if e['type'] == 'directory'}
