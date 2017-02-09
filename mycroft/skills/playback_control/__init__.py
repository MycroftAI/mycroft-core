import sys
from os.path import dirname, abspath, basename

from mycroft.skills.media import MediaSkill
from adapt.intent import IntentBuilder
from mycroft.messagebus.message import Message
from mycroft.configuration import ConfigurationManager
from mycroft.skills.audioservice import AudioBackend

from os.path import dirname

from mycroft.util.log import getLogger

config = ConfigurationManager.get().get('Audio')
logger = getLogger(abspath(__file__).split('/')[-2])
__author__ = 'forslund'


class PlaybackControlSkill(MediaSkill):
    def __init__(self):
        super(PlaybackControlSkill, self).__init__('Playback Control Skill')
        logger.info('Playback Control Inited')

    def initialize(self):
        logger.info('initializing Playback Control Skill')
        super(PlaybackControlSkill, self).initialize()
        self.load_data_files(dirname(__file__))

    def handle_next(self, message):
        self.emitter.emit(Message('MycroftAudioServiceNext'))
    
    def handle_prev(self, message):
        self.emitter.emit(Message('MycroftAudioServicePrev'))

    def handle_pause(self, message):
        self.emitter.emit(Message('MycroftAudioServicePause'))

    def handle_play(self, message):
        """Resume playback if paused"""
        self.emitter.emit(Message('MycroftAudioServiceResume'))

    def handle_currently_playing(self, message):
        return

    def stop(self, message=None):
        logger.info("Stopping audio")
        self.emitter.emit(Message('MycroftAudioServiceStop'))


def create_skill():
    return PlaybackControlSkill()
