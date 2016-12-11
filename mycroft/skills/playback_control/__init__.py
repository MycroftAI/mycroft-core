import sys
from os.path import dirname, abspath, basename

from mycroft.skills.media import MediaSkill
from adapt.intent import IntentBuilder
from mycroft.messagebus.message import Message
from mycroft.configuration import ConfigurationManager
import subprocess

import time

import requests

from os.path import dirname

from mycroft.util.log import getLogger

config = ConfigurationManager.get().get('audio')
logger = getLogger(abspath(__file__).split('/')[-2])
__author__ = 'forslund'

sys.path.append(abspath(dirname(__file__)))
if config.get('audio.mopidy', 'False') == 'True':
    MopidyService = __import__('mopidy_service').MopidyService
if config.get('audio.vlc', 'False') == 'True':
    VlcService = __import__('vlc_service').VlcService


class Mpg123Service():
    def __init__(self, config, emitter):
        self.config = config
        self.process = None
        self.emitter = emitter 
        self.emitter.on('Mpg123ServicePlay', self._play)

    @property
    def name(self):
        return self.config.get('audio.mpg123.name', 'mpg123')

    def supported_uris(self):
        return ['file', 'http']

    def clear_list(self):
        self.tracks = []
    
    def add_list(self, tracks):
        self.tracks = tracks
        logger.info("Track list is " + str(tracks))

    def _play(self, message):
        logger.info('Mpg123Service._play')
        track = self.tracks[self.index]
        self.process = subprocess.Popen(['mpg123', track])
        self.process.communicate()
        self.process = None
        self.index += 1
        if self.index >= len(self.tracks):
            self.emitter.emit(Message('Mpg123ServicePlay'))

    def play(self):
        logger.info('Call Mpg123ServicePlay')
        self.index = 0
        self.emitter.emit(Message('Mpg123ServicePlay'))

    def stop(self):
        logger.info('Mpg123ServiceStop')
        self.clear_list()
        if self.process:
            self.process.terminate()
            self.process = None

    def pause(self):
        pass

    def resume(self):
        pass

    def next(self):
        self.process.terminate()

    def previous(self):
        pass

    def lower_volume(self):
        pass
        
    def restore_volume(self):
        pass

    def track_info(self):
        return {}


class PlaybackControlSkill(MediaSkill):
    def __init__(self):
        super(PlaybackControlSkill, self).__init__('Playback Control Skill')
        self.volume_is_low = False
        self.current = None
        logger.info('Playback Control Inited')
        self.service = []

    def initialize(self):
        logger.info('initializing Playback Control Skill')
        super(PlaybackControlSkill, self).initialize()
        self.load_data_files(dirname(__file__))

        if config.get('audio.vlc', 'False') == 'True':
            logger.info('starting VLC service')
            self.service.append(VlcService(config, self.emitter))
        if config.get('audio.mopidy', 'False') == 'True':
            logger.info('starting Mopidy service')
            self.service.append(MopidyService(config, self.emitter))
        logger.info('starting Mpg123 service')
        self.service.append(Mpg123Service(config, self.emitter))
        self.emitter.on('MycroftAudioServicePlay', self._play)
        self.emitter.on('MycroftAudioServiceTrackInfo', self._track_info)

    def play(self, tracks):
        logger.info('play')
        self.stop()
        uri_type = tracks[0].split(':')[0]
        logger.info('uri_type: ' + uri_type)
        for s in self.service:
            logger.info(str(s))
            if uri_type in s.supported_uris():
                service = s
                break
        else:
            return
        logger.info('Clear list')
        service.clear_list()
        logger.info('Add tracks' + str(tracks))
        service.add_list(tracks)
        logger.info('Playing')
        service.play()
        self.current = service

    def _play(self, message):
        logger.info('MycroftAudioServicePlay')
        logger.info(message.metadata['tracks'])

        tracks = message.metadata['tracks']
        self.play(tracks)

    def stop(self, message=None):
        logger.info('stopping all playing services')
        if self.current:
            self.current.stop()
            self.current = None

    def handle_next(self, message):
        if self.current:
            self.current.next()

    def handle_prev(self, message):
        if self.current:
            self.current.previous()

    def handle_pause(self, message):
        if self.current:
            self.current.pause()

    def handle_play(self, message):
        """Resume playback if paused"""
        if self.current:
            self.current.resume()

    def lower_volume(self, message):
        logger.info('lowering volume')
        if self.current:
            self.current.lower_volume()
            self.volume_is_low = True

    def restore_volume(self, message):
        logger.info('maybe restoring volume')
        if self.current:
            self.volume_is_low = False
            time.sleep(2)
            if not self.volume_is_low:
                logger.info('restoring volume')
                self.current.restore_volume()

    def handle_currently_playing(self, message):
        return

    def _track_info(self, message):
        if self.current:
            track_info = self.current.track_info()
        else:
            track_info = {}
        self.emitter.emit(Message('MycroftAudioServiceTrackInfoReply',
                                  metadata=track_info))

def create_skill():
    return PlaybackControlSkill()
