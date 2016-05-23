from mycroft.skills.media import MediaSkill
from adapt.intent import IntentBuilder

from mycroft.skills.swedishradio import sr

from os.path import dirname
import time
import subprocess

from mycroft.util.log import getLogger
logger = getLogger(__name__)

__author__ = 'forslund'


class SwedishRadio(MediaSkill):
    def __init__(self):
        super(SwedishRadio, self).__init__('Swedish Radio')
        self.sr = sr.SwedishRadio()
        self.process = None

    def initialize(self):
        logger.info('initializing SwedishRadio')
        self.load_data_files(dirname(__file__))
        super(SwedishRadio, self).initialize()

        for c in self.sr.channels.keys():
            self.register_vocabulary(c, 'ChannelKeyword')
        intent = IntentBuilder('PlayChannelIntent' + self.name)\
            .require('PlayKeyword')\
            .require('ChannelKeyword')\
            .build()
        self.register_intent(intent, self.handle_play_channel)
        intent = IntentBuilder('PlayFromIntent' + self.name)\
            .require('PlayKeyword')\
            .require('ChannelKeyword')\
            .reqyure('FromKeyword')\
            .require('NameKeyword')\
            .build()
        self.register_intent(intent, self.handle_play_channel)

    def play(self):
        super(SwedishRadio, self).play()
        self.speak_dialog('listening_to', {'channel': self.channel})
        time.sleep(2)
        stream_url = self.sr.channels[self.channel].stream_url
        self.process = subprocess.Popen(['mpg123', stream_url])

    def get_available(self, channel_name):
        logger.info(channel_name)
        if channel_name in self.sr:
            logger.info('Registring play intention...')
            return channel_name
        else:
            return None

    def prepare(self, channel_name):
        self.channel = channel_name

    def handle_play_channel(self, message):
        c = message.metadata.get('ChannelKeyword')
        self.prepare(c)
        self.play()

    def handle_stop(self, message):
        logger.info('Handling stop request')
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
            self.channel = None
        super(SwedishRadio, self).handle_stop(message)

    def handle_currently_playing(self, message):
        if self.channel is not None:
            self.speak_dialog('currently_playing', {'channel': self.channel})


def create_skill():
    return SwedishRadio()

