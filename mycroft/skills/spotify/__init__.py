from mycroft.skills.media import MediaSkill
from mycroft.skills.media import mopidy
from adapt.intent import IntentBuilder
from mycroft.messagebus.message import Message

import time

from os.path import dirname
from os import listdir

from mycroft.util.log import getLogger
logger = getLogger(__name__)

__author__ = 'forslund'


class Spotify(MediaSkill):
    def __init__(self):
        super(Spotify, self).__init__('Spotify')
        self.tracks = None
        self.volume_is_low = False

    def _connect(self, message):
        url = self.base_conf.get('mopidy_url', None)
        if self.config:
            url = self.config.get('mopidy_url', url)
        try:
            self.mopidy = mopidy.Mopidy(url)
        except:
            logger.info('Could not connect to server, retrying in 10 sec')
            time.sleep(10)
            self.emitter.emit(Message(self.name + '.connect'))
            return

        p = self.mopidy.get_playlists('spotify')
        self.playlist = {
            e['name'].split('(by')[0].strip().lower(): e for e in p
        }

        for p in self.playlist.keys():
            logger.debug("Playlist: " + p)
            self.register_vocabulary(p, 'PlaylistKeyword' + self.name)
        intent = IntentBuilder('PlayPlaylistIntent' + self.name)\
            .require('PlayKeyword')\
            .require('PlaylistKeyword'+self.name)\
            .build()
        self.register_intent(intent, self.handle_play_playlist)

        self.register_regex("(?P<Source>.*)")
        intent = IntentBuilder('PlayFromIntent' + self.name)\
            .require('PlayKeyword')\
            .require('Source')\
            .require('FromKeyword')\
            .require('NameKeyword')\
            .build()
        self.register_intent(intent, self.handle_play_from)

    def initialize(self):
        logger.info('initializing Spotify skill')
        super(Spotify, self).initialize()
        self.load_data_files(dirname(__file__))

        self.emitter.on(self.name + '.connect', self._connect)
        self.emitter.emit(Message(self.name + '.connect'))

    def play(self):
        super(Spotify, self).play()
        self.speak_dialog('listening_to', {'tracks': self.tracks['name']})
        time.sleep(2)
        self.mopidy.add_list(self.tracks['uri'])
        logger.info(self.mopidy.play())
        self.tracks = None

    def get_available(self, name):
        logger.info(name)
        tracks = None
        if name in self.playlist:
            logger.info('Found track among loaded playlists')
            tracks = self.playlist[name]
        else:
            results = self.mopidy.find_album(name, 'spotify')
            if len(results) > 0:
                tracks = results[0]
        return tracks

    def prepare(self, tracks):
        logger.info('found tracks: ' + str(self.tracks))
        self.tracks = tracks

    def handle_play_playlist(self, message):
        p = message.metadata.get('PlaylistKeyword' + self.name)
        self.prepare(self.playlist[p])
        self.play()

    def handle_play_from(self, message):
        logger.info('Play From request')
        utt = message.metadata['utterance']
        fr = message.metadata.get('FromKeyword')
        pl = message.metadata.get('PlayKeyword')
        skill = utt.split(fr)[1].strip()
        logger.info(skill + " " + self.name)
        if skill == self.name.lower():
            name = utt.split(fr)[0].split(pl)[1].strip()
            logger.info(name)
            media = self.get_available(name)
            if media is not None:
                self.prepare(media)
                self.play()
        elif fr is not None:
            name = message.metadata.get('Source') + ' ' + fr + ' ' + skill
            self.tracks = self.get_available(name)
            if self.tracks is not None:
                self.play()

    def handle_stop(self, message=None):
        logger.info('Handling stop request')
        self.mopidy.clear_list()
        self.mopidy.stop()
        logger.info("Super")
        super(Spotify, self).handle_stop(message)

    def handle_next(self, message):
        self.mopidy.next()

    def handle_prev(self, message):
        self.mopidy.previous()

    def handle_pause(self, message):
        self.mopidy.pause()

    def handle_resume(self, message):
        self.mopidy.resume()

    def lower_volume(self, message):
        self.mopidy.lower_volume()
        self.volume_is_low = True

    def restore_volume(self, message):
        self.volume_is_low = False
        time.sleep(2)
        if not self.volume_is_low:
            logger.info('restoring volume')
            self.mopidy.restore_volume()

    def handle_currently_playing(self, message):
        current_track = self.mopidy.currently_playing()
        if current_track is not None:
            data = {'current_track': current_track['name'],
                    'artist': current_track['artists'][0]['name']}
            self.speak_dialog('currently_playing', data)


def create_skill():
    return Spotify()
