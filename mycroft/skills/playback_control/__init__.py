import sys
from os.path import dirname, abspath, basename

from mycroft.skills.media import MediaSkill
from adapt.intent import IntentBuilder
from mycroft.messagebus.message import Message
from mycroft.configuration import ConfigurationManager
from mycroft.skills.audioservice import AudioBackend
import subprocess

import time

import requests

from os.path import dirname

from mycroft.util.log import getLogger

config = ConfigurationManager.get().get('Audio')
logger = getLogger(abspath(__file__).split('/')[-2])
__author__ = 'forslund'
sys.path.append(abspath(dirname(__file__)))
MopidyService = __import__('mopidy_service').MopidyService

# only import services that are configured
for b in config['backends']:
    logger.debug(b)
    b = config['backends'][b]
    if b['type'] == 'vlc' and b.get('active', False):
        VlcService = __import__('vlc_service').VlcService
    if b['type'] == 'chromecast' and b.get('active', False):
        ChromecastService = __import__('chromecast_service').ChromecastService

if config.get('autodetect-chromecasts', False):
    autodetect_chromecasts = __import__('chromecast_service').autodetect


class Mpg123Service(AudioBackend):
    def __init__(self, config, emitter, name='mpg123'):
        self.config = config
        self.process = None
        self.emitter = emitter
        self.name = name

        self.emitter.on('Mpg123ServicePlay', self._play)

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

        # Add all manually specified services
        for name in config['backends']:
            b = config['backends'][name]
            logger.debug(b)
            if b['type'] == 'vlc' and b.get('active', False):
                logger.info('starting VLC service')
                self.service.append(VlcService(b, self.emitter, name))
            if b['type'] == 'mopidy' and b.get('active', False):
                logger.info('starting Mopidy service')
                self.service.append(MopidyService(b, self.emitter, name))
            if b['type'] == 'mpg123' and b.get('active', False):
                logger.info('starting Mpg123 service')
                self.service.append(Mpg123Service(b, self.emitter, name))
            if b['type'] == 'chromecast' and b.get('active', False):
                logger.info('starting Chromecast service')
                self.service.append(ChromecastService(b, self.emitter, name))

        # Autodetect chromecast devices
        if config.get('autodetect-chromecasts', False):
            logger.info('Autodetecting Chromecasts')
            chromecasts = autodetect_chromecasts({}, self.emitter)
            self.service = self.service + chromecasts

        default_name = config.get('default-backend', '')
        for s in self.service:
            if s.name == default_name:
                self.default = s
                break
        else:
            self.default = None
        logger.info(self.default)

        self.emitter.on('MycroftAudioServicePlay', self._play)
        self.emitter.on('MycroftAudioServiceTrackInfo', self._track_info)

    def play(self, tracks, prefered_service):
        logger.info('play')
        self.stop()
        uri_type = tracks[0].split(':')[0]
        logger.info('uri_type: ' + uri_type)
        # check if user requested a particular service
        if prefered_service and uri_type in prefered_service.supported_uris():
            service = prefered_service
        # check if default supports the uri
        elif self.default and uri_type in self.default.supported_uris():
            logger.info("Using default backend")
            logger.info(self.default.name)
            service = self.default
        else:  # Check if any other service can play the media
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
        logger.info(message.data['tracks'])

        tracks = message.data['tracks']

        # Find if the user wants to use a specific backend
        for s in self.service:
            logger.info(s.name)
            if s.name in message.data['utterance']:
                prefered_service = s
                logger.info(s.name + ' would be prefered')
                break
        else:
            prefered_service = None
        self.play(tracks, prefered_service)

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
                                  data=track_info))


def create_skill():
    return PlaybackControlSkill()
