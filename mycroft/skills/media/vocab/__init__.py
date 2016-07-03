from os.path import join, dirname

from adapt.intent import IntentBuilder
from mycroft.skills import time_rules
from mycroft.skills.core import MycroftSkill
from mycroft.messagebus.message import Message
from mycroft.configuration.config import ConfigurationManager

from mycroft.util.log import getLogger
import mopidy

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
        config = ConfigurationManager.get_config()
        self.base_conf = config.get('Media')

    def initialize(self):
        logger.info('Initializing MediaSkill commons')
        logger.info('loading vocab files from ' + join(dirname(__file__),
                    'vocab', self.lang))
        self.load_vocab_files(join(dirname(__file__), 'vocab', self.lang))

        self.register_vocabulary(self.name, 'NameKeyword')
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

        intent = IntentBuilder('StopIntent').require('StopKeyword')
        self.register_intent(intent, self.handle_stop)

        intent = IntentBuilder('PauseIntent').require('PauseKeyword')
        self.register_intent(intent, self.handle_pause)

        intent = IntentBuilder('ResumeIntent').require('ResumeKeyword')
        self.register_intent(intent, self.handle_resume)

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
        logger.info('handle_next not implemented')

    def handle_prev(self, message):
        """
           handle_prev() should be implemented by the skill to switch to
           previous song/channel/video in queue
        """
        logger.info('handle_prev not implemented')

    def handle_currently_playing(self, message):
        """
           handle_currently_playing() should be implemented to tell the user
           what is currently playing
        """
        logger.info('handle_currently_playing not implemented')

    def play(self):
        """ Stop currently playing media before starting the new. """
        logger.info('Stopping currently playing media if any')
        self.emitter.emit(Message('mycroft.media.stop'))

    def handle_pause(self, message):
        """ handle_pause() should pause currently playing media """
        logger.info('handle_pause not implemented')

    def handle_resume(self, message):
        """ handle_resume() should resume paused media """
        logger.info('handle_resume not implemented')

    def handle_stop(self, message):
        """
           handle_stop() should be implemented to stop currently playing media
        """
        logger.info('handle_stop not implemented')

    def stop(self):
        logger.debug('No stop method implemented')

    def lower_volume(self, message):
        logger.debug('Lower volume not implemented')

    def restore_volume(self, message):
        logger.debug('Restore volume not implemented')

    def _set_sink(self, message):
        """ Selects the output device """
        pass
