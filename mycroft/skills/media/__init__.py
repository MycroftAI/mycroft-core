from os.path import join, dirname

from adapt.intent import IntentBuilder
from mycroft.skills import time_rules
from mycroft.skills.core import MycroftSkill
from mycroft.messagebus.message import Message

from mycroft.util.log import getLogger
logger = getLogger(__name__)

import mopidy

__author__ = 'forslund'


class MediaSkill(MycroftSkill):
    def __init__(self, name):
        super(MediaSkill, self).__init__(name)
        self.isPlaying = False
        #TODO load config

    def initialize(self):
        logger.info('Initializing MediaSkill commons')
        logger.info('loading vocab files from ' + join(dirname(__file__), 'vocab', self.lang))
        self.load_vocab_files(join(dirname(__file__), 'vocab', self.lang))

        self.register_vocabulary(self.name, 'NameKeyword')

        intent = IntentBuilder('NextIntent').require('NextKeyword')
        self.register_intent(intent, self.handle_next)
        
        intent = IntentBuilder('PrevIntent').require('PrevKeyword')
        self.register_intent(intent, self.handle_prev)

        intent = IntentBuilder('StopIntent').require('StopKeyword')
        self.register_intent(intent, self.handle_stop)

        intent = IntentBuilder('CurrentlyPlayingIntent')\
            .require('CurrentlyPlayingKeyword')
        self.register_intent(intent, self.handle_currently_playing)
        self.emitter.on('mycroft.media.stop', self.handle_stop)

    def handle_next(self, message):
        pass

    def handle_prev(self, message):
        pass

    def handle_currently_playing(self, message):
        pass

    def play(self):
        """ Stop currently playing media before starting the new. """
        logger.info('Stopping currently playing media if any')

        self.emitter.emit(Message("mycroft.media.stop"))

    def handle_pause(self, message):
        pass

    def handle_stop(self, message):
        logger.info('handling stop request')

    def stop(self):
        logger.debug('No stop method implemented')

    def _set_sink(self, message):
        """ Selects the output device """
        pass
