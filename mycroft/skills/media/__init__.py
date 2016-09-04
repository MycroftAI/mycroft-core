from adapt.intent import IntentBuilder
from os.path import join, dirname

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

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
        self.base_conf = config.get('MediaSkill')

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

        intent = IntentBuilder('CurrentlyPlayingIntent') \
            .require('CurrentlyPlayingKeyword')
        self.register_intent(intent, self.handle_currently_playing)

    def _register_event_handlers(self):
        """
           Register event handlers for stopping currently playing media
           when new media is started and handlers for lowering media volume
           while mycroft is speaking.
        """
        self.emitter.on('mycroft.media.stop', self._media_stop)
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

    def before_play(self):
        """
           Stop currently playing media before starting the new. This method
           should always be called before the skill starts playback.
        """
        logger.info('Stopping currently playing media if any')
        self.emitter.emit(Message('mycroft.media.stop', {'origin': self.name}))

    def handle_pause(self, message):
        """ handle_pause() should pause currently playing media """
        logger.debug('handle_pause not implemented in ' + self.name)

    def handle_play(self, message):
        """ handle_play() generic play handler. Should resume paused media
            and/or implement generic playback functionality.

            The skill creator should make sure to call before_play() here
            if applicable"""
        logger.debug('handle_play not implemented in ' + self.name)

    def _media_stop(self, message):
        """ handler for 'mycroft.media.stop' """
        origin = message.data.get('origin', '')
        if origin != self.name:
            self.stop()

    def stop(self):
        """
           stop() should be implemented to stop currently playing media. This
           function will be called by either the general mycroft 'stop'
           functionallity or internal message bus communication.
        """
        logger.debug('Stop not implemented in ' + self.name)

    def lower_volume(self, message):
        logger.debug('Lower volume not implemented in ' + self.name)

    def restore_volume(self, message):
        logger.debug('Restore volume not implemented in ' + self.name)

    def _set_output_device(self, message):
        """ Selects the output device """
        pass
