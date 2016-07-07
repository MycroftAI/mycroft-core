from os.path import join, dirname

from adapt.intent import IntentBuilder
from mycroft.skills import time_rules
from mycroft.skills.core import MycroftSkill
from mycroft.messagebus.message import Message
from mycroft.configuration import ConfigurationManager

from mycroft.util.log import getLogger
import mycroft.skills.media.mopidy

logger = getLogger(__name__)

__author__ = 'forslund'


class MediaSkill(MycroftSkill):
    """
        The MediaSkill class is a base class for media skills containing
        vocabulary and intents for the common functions expected by a media
        skill. In addition event handlers to lower volume when mycroft starts
        to speak and raise it again when (s)he stops.

        But wait there is one more thing! A small event emitter and matching
        handler to stop media currently playing when new media is started.
    """
    def __init__(self, name):
        super(MediaSkill, self).__init__(name)
        self.isPlaying = False
        config = ConfigurationManager.get()
        self.base_conf = config.get('Media')

    def initialize(self):
        logger.info('Initializing MediaSkill commons')
        logger.info('loading vocab files from ' + join(dirname(__file__),
                    'vocab', self.lang))
        self.load_vocab_files(join(dirname(__file__), 'vocab', self.lang))

        self._register_common_intents()
        self._register_event_handlers()

    def _register_common_intents(self):
        """
           Register common intents, these include basically all intents
           except the intents to start playback.
        """
        intent = IntentBuilder('NextIntent').require('NextKeyword')
        self.register_intent(intent, self.handle_next)

        intent = IntentBuilder('PrevIntent').require('PrevKeyword')
        self.register_intent(intent, self.handle_prev)

        intent = IntentBuilder('PauseIntent').require('PauseKeyword')
        self.register_intent(intent, self.handle_pause)

        intent = IntentBuilder('PlayIntent') \
            .one_of('PlayKeyword', 'ResumeKeyword')
        self.register_intent(intent, self.handle_play)

        intent = IntentBuilder('CurrentlyPlayingIntent')\
            .require('CurrentlyPlayingKeyword')
        self.register_intent(intent, self.handle_currently_playing)

    def _register_event_handlers(self):
        """
           Register event handlers for stopping currently playing media
           when new media is started and handlers for lowering media volume
           while mycroft is speaking.
        """
        self.emitter.on('mycroft.media.stop', self.handle_stop)
        self.emitter.on('recognizer_loop:audio_output_start',
                        self.lower_volume)
        self.emitter.on('recognizer_loop:audio_output_end',
                        self.restore_volume)

    def handle_next(self, message):
        """
           handle_next() should be implemented by the skill to switch to next
           song/channel/video in queue.
        """
        logger.debug('handle_next not implemented in ' + self.name)

    def handle_prev(self, message):
        """
           handle_prev() should be implemented by the skill to switch to
           previous song/channel/video in queue
        """
        logger.debug('handle_prev not implemented in ' + self.name)

    def handle_currently_playing(self, message):
        """
           handle_currently_playing() should be implemented to tell the user
           what is currently playing
        """
        logger.debug('handle_currently_playing not implemented in ' +
                     self.name)

    def play(self):
        """ Stop currently playing media before starting the new. """
        logger.info('Stopping currently playing media if any')
        self.emitter.emit(Message('mycroft.media.stop'))

    def handle_pause(self, message):
        """ handle_pause() should pause currently playing media """
        logger.debug('handle_pause not implemented in ' + self.name)

    def handle_play(self, message):
        """ handle_play() generic play handler. Should resume paused media
            and/or implement generic playback functionality."""
        logger.debug('handle_play not implemented in ' + self.name)

    def handle_stop(self, message):
        """
           handle_stop() should be implemented to stop currently playing media
        """
        logger.debug('handle_stop not implemented in ' + self.name)

    def stop(self):
        self.handle_stop(None)

    def lower_volume(self, message):
        logger.debug('Lower volume not implemented in ' + self.name)

    def restore_volume(self, message):
        logger.debug('Restore volume not implemented in ' + self.name)

    def _set_sink(self, message):
        """ Selects the output device """
        pass
